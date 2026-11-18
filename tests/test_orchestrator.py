"""Seam 2: the turn orchestrator with a scripted fake Claude client and an event collector."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from pidm.claude import ClaudeError, Usage
from pidm.engine import load_state
from pidm.models import Campaign, RollRecord, Session, Turn
from pidm.campaign import Setup, start_campaign
from pidm.orchestrator import CampaignEnded, TurnAlreadyRunning, TurnOrchestrator
from pidm.templates import create_character

from conftest import Events, FakeClaude, fixture_bible, scripted_rng, text, tool

@pytest.fixture
def world(factory):
    def make(template="fighter"):
        with factory() as db:
            camp = Campaign(name="Test", premise="Bandits on the north road.")
            create_character(camp, template)
            sess = Session(campaign=camp)
            db.add(camp)
            db.commit()
            return sess.id
    return make


def final_user_message(claude, request=0):
    content = claude.requests[request]["messages"][-1]["content"]
    return content if isinstance(content, str) else "".join(b.get("text", "") for b in content)


def system_text(request):
    return "".join(b["text"] for b in request["system"])


def character(factory, session_id):
    db = factory()
    return load_state(db, session_id, None).character


def turns(factory, session_id):
    with factory() as db:
        return db.scalars(select(Turn).where(Turn.session_id == session_id).order_by(Turn.seq)).all()


def test_tool_round_then_narration_commits_turn_rolls_and_state(factory, world):
    sid = world()
    claude = FakeClaude(tool("apply_damage", target="character", amount="1d6", damage_type="fire"),
                        text("Flames lick your boots."))
    ev = Events()
    orch = TurnOrchestrator(factory, claude, rng=scripted_rng([4]))
    turn = orch.run_turn(sid, "I kick the brazier", ev)
    assert ev.kinds() == ["roll", "narration_delta", "state_changed", "turn_done"]
    assert ev[0][1]["total"] == 4 and ev[1][1]["text"] == "Flames lick your boots."
    assert turn.status == "committed" and turn.seq == 0
    assert (turn.tokens_in, turn.tokens_out, turn.tokens_cached) == (200, 40, 120)
    assert character(factory, sid).hp_current == 8
    with factory() as db:
        rolls = db.scalars(select(RollRecord)).all()
        assert [(r.purpose, r.total) for r in rolls] == [("Bram takes fire damage", 4)]
    # The request carried the state snapshot and the player's action in the final user message.
    first = final_user_message(claude)
    assert '"hp":12' in first and first.endswith("Player action: I kick the brazier")


def test_tool_result_errors_go_back_to_claude(factory, world):
    sid = world()
    claude = FakeClaude(tool("attack", target="Goblin 1", weapon="longsword"), text("You swing at nothing."))
    TurnOrchestrator(factory, claude).run_turn(sid, "attack", Events())
    result = claude.requests[1]["messages"][-1]["content"][0]
    assert result["is_error"] and "No active Encounter" in result["content"]


def test_prose_in_a_tool_round_is_stripped_and_never_shown(factory, world):
    # ADR 0003
    sid = world()
    claude = FakeClaude([text("You hit!"), tool("roll", expr="1d20", purpose="luck")], text("The die settles."))
    ev = Events()
    TurnOrchestrator(factory, claude, rng=scripted_rng([7])).run_turn(sid, "roll", ev)
    assistant = claude.requests[1]["messages"][-2]
    assert assistant["role"] == "assistant" and [b["type"] for b in assistant["content"]] == ["tool_use"]
    # Every round streams; a round that turns out to call tools is discarded, so only the last stays.
    assert [(e, p.get("text")) for e, p in ev if e.startswith("narration")] == [
        ("narration_delta", "You hit!"), ("narration_discard", None), ("narration_delta", "The die settles.")]
    assert ev[[e for e, _ in ev].index("narration_discard")][1] == {"turn_seq": 0}


def test_tool_round_cap_forces_a_narration_only_call(factory, world):
    sid = world()
    rounds = [tool("roll", expr="1d4", purpose=f"r{i}") for i in range(4)]
    claude = FakeClaude(*rounds, text("Enough dice."))
    ev = Events()
    turn = TurnOrchestrator(factory, claude, round_cap=4, rng=scripted_rng([1, 2, 3, 4])).run_turn(sid, "x", ev)
    assert [r["tools_enabled"] for r in claude.requests] == [True, True, True, True, False]
    assert turn.narration == "Enough dice." and turn.status == "committed"
    assert ev.kinds()[-3:] == ["narration_delta", "state_changed", "turn_done"]


def test_failed_turn_leaves_state_unchanged_and_saves_a_failed_row(factory, world):
    sid = world()
    claude = FakeClaude(tool("apply_damage", target="character", amount="5", damage_type="fire"),
                        ClaudeError("overloaded", Usage(50, 0, 0)))
    ev = Events()
    turn = TurnOrchestrator(factory, claude).run_turn(sid, "I touch the rune", ev)
    assert turn.status == "failed" and turn.tokens_in == 150
    assert ev.kinds()[-1] == "error" and ev[-1][1]["retryable"]
    assert character(factory, sid).hp_current == 12
    with factory() as db:
        assert db.scalars(select(RollRecord)).all() == []
    # Retry is a new Turn with a new seq.
    TurnOrchestrator(factory, FakeClaude(text("ok"))).run_turn(sid, "I touch the rune", Events())
    assert [(t.seq, t.status) for t in turns(factory, sid)] == [(0, "failed"), (1, "committed")]


def test_a_second_turn_is_refused_while_one_runs(factory, world):
    sid = world()
    orch = TurnOrchestrator(factory, None)
    seen = []

    class Reentrant(FakeClaude):
        def send(self, **kw):
            with pytest.raises(TurnAlreadyRunning):
                orch.run_turn(sid, "again", Events())
            seen.append(orch.running)
            return super().send(**kw)

    orch.client = Reentrant(text("fine"))
    orch.run_turn(sid, "first", Events())
    assert seen == [True] and not orch.running


def test_history_carries_the_last_turns_as_action_and_narration_pairs(factory, world):
    sid = world()
    orch = TurnOrchestrator(factory, FakeClaude(text("One."), text("Two."), text("Three.")), history_turns=2)
    for action in ("a", "b", "c"):
        orch.run_turn(sid, action, Events())
    msgs = orch.client.requests[2]["messages"]
    assert [(m["role"], m["content"]) for m in msgs[:4]] == [
        ("user", "a"), ("assistant", "One."), ("user", "b"), ("assistant", "Two.")]
    orch.client.script.append(text("Four."))
    orch.run_turn(sid, "d", Events())
    assert orch.client.requests[3]["messages"][0]["content"] == "b"


def test_m1_exit_scene(factory, world):
    """M1 exit: a skill check, a contest, a fight against three monsters resolved with resolve_npc_turns,
    a condition applied, and death saves, played as four Turns with scripted Claude and dice."""
    sid = world("rogue")  # Pip: HP 10, AC 14, Dex +3, Str -1, Lucky (so no scripted 1s on Pip's d20s)
    rng, replies = [], []

    def turn(calls, narration, dice):
        rng.extend(dice)
        replies.extend([[c] for c in calls] + [text(narration)])

    turn([tool("skill_check", skill="perception", dc=15)], "Fresh tracks lead into the ravine.",
         [12])                                    # 12+3 = 15: success
    turn([tool("start_encounter", monsters=[{"monster": "goblin", "count": 2}, {"monster": "wolf"}])],
         "Two goblins and a wolf burst out!",
         [10, 1, 1, 1])                           # Pip 13; goblins 3, 3; wolf 3 (wolf has higher Dex)
    turn([tool("contest", a="character", b="Goblin 1", effect="shove_prone"), tool("resolve_npc_turns")],
         "You shove a goblin into the dirt.",
         [15, 3,                                  # Athletics 15-1 = 14 vs goblin Acrobatics 3+2 = 5
          2, 2, 2])                               # wolf, Goblin 1 (stands up), Goblin 2 all miss AC 14
    turn([tool("attack", target="Goblin 1", weapon="shortsword"), tool("resolve_npc_turns")],
         "The goblin falls, but the wolf drags you down.",
         [15, 4,                                  # 15+5 hits AC 15; 1d6 4+3 = 7 kills Goblin 1
          18, 4, 4,                               # wolf bite 22 hits; 2d4+2 = 10: Pip to 0 HP
          2, 3,                                   # Goblin 2 vs unconscious Pip: advantage, 3+4 misses
          12])                                    # Pip's death save at the start of round 3: success
    ev = Events()
    orch = TurnOrchestrator(factory, FakeClaude(*replies), rng=scripted_rng(rng))
    for action in ("I search the road", "I creep into the ravine", "I shove the nearest goblin",
                   "I stab the goblin"):
        orch.run_turn(sid, action, ev)

    assert [t.status for t in turns(factory, sid)] == ["committed"] * 4
    assert ev.kinds().count("turn_done") == 4 and "error" not in ev.kinds()
    pip = character(factory, sid)
    assert pip.hp_current == 0 and (pip.death_successes, pip.death_failures) == (1, 0)
    assert {c["name"] for c in pip.conditions} == {"unconscious", "prone"}
    db = factory()
    enc = load_state(db, sid, None).encounter
    assert [(c.name, c.status) for c in enc.combatants] == [
        ("Goblin 1", "dead"), ("Goblin 2", "active"), ("Wolf 1", "active")]
    # Each roll event carries its outcome as it happens (initiative and damage rolls have none).
    outcomes = [p["outcome"] for e, p in ev if e == "roll" and p["outcome"]]
    assert outcomes == ["success", "win", "loss", "miss", "miss", "miss", "hit", "hit", "miss", "success"]




def test_an_action_naming_a_rule_carries_its_rule_sections(factory, world):
    sid = world()
    claude = FakeClaude(text("You duck behind the wall."))
    TurnOrchestrator(factory, claude).run_turn(sid, "I take cover behind the wall", Events())
    msg = final_user_message(claude)
    state, rules = msg.index("<state>"), msg.index("<rules>")
    assert state < rules < msg.index("Player action: I take cover behind the wall")
    assert msg.count("<section>") == 2 and "<section>Cover</section>" in msg
    # The long Pits section is cut to about 600 tokens, with a pointer to the full text.
    assert "lookup_rule returns the full text" in msg


def test_an_action_naming_no_rule_carries_no_rule_text(factory, world):
    sid = world()
    claude = FakeClaude(text("The innkeeper nods."))
    TurnOrchestrator(factory, claude).run_turn(sid, "I order an ale", Events())
    assert "<rules>" not in final_user_message(claude)


def test_m2_exit_scene(factory, world):
    """M2 exit: "I grapple the goblin" puts the Grappling Rule section in context and leads to a contest."""
    sid = world("fighter")  # Bram: Athletics +5
    claude = FakeClaude([tool("start_encounter", monsters=[{"monster": "goblin"}])],
                        [tool("contest", a="character", b="Goblin 1", effect="grapple")],
                        text("You wrestle the goblin to a standstill."))
    rng = scripted_rng([20, 1,   # Bram 22 acts before the goblin
                        15, 2])  # Athletics 20 vs goblin Acrobatics 2+2 = 4
    TurnOrchestrator(factory, claude, rng=rng).run_turn(sid, "I grapple the goblin", Events())
    assert "<section>Making an Attack > Melee Attacks > Grappling</section>" in final_user_message(claude)
    result = claude.requests[2]["messages"][-1]["content"][0]
    assert "Goblin 1 is grappled" in result["content"]


# --- M3: story director --------------------------------------------------------------------

@pytest.fixture
def story_world(factory):
    def make(template="fighter"):
        setup = Setup("dark fantasy", "grim", "one-shot", lines="harm to children", veils="torture")
        return start_campaign(factory, setup, template, None, bible=fixture_bible()).id
    return make


def campaign(factory, session_id):
    return load_state(factory(), session_id, None).campaign


def test_the_director_block_and_the_bible_reach_claude_every_turn(factory, story_world):
    sid = story_world()
    claude = FakeClaude(text("Fog."), text("More fog."))
    orch = TurnOrchestrator(factory, claude)
    orch.run_turn(sid, "I look around", Events())
    orch.run_turn(sid, "I wait", Events())
    system = system_text(claude.requests[0])
    assert system_text(claude.requests[1]) == system  # byte-identical across Turns (cache breakpoint 1)
    assert "The Drowned Bell" in system and "secret.rope" in system and "Abbess Varn" in system
    assert "Lines (never show): harm to children" in system and "Veils (keep off-screen): torture" in system
    msg = final_user_message(claude)
    director = msg[msg.index("<director>"):msg.index("</director>")]
    assert msg.index("</state>") < msg.index("<director>") < msg.index("Player action: I look around")
    assert "Act 1 of 1: Find who is taking the villagers" in director
    assert "Location: loc.shore (The Reed Shore)" in director
    assert "- act1.undercroft: Get into the flooded undercroft beneath the sunken chapel. (requires secret.sluice)" in director
    assert "- clue.sluice.3: A cultist's map" in director and "clue.sluice.1" not in director  # local Clues only
    assert "Learned Secrets: none" in director
    assert "The spring tide rises 0/6 (clock.tide, main)" in director and "The cult grows suspicious 0/4" in director
    assert "Turns since progress: 0" in director and "STALL" not in director


def test_the_opening_scene_is_turn_0(factory, story_world):
    sid = story_world()
    claude = FakeClaude(text("Fog on the Reed Shore... What do you do?"))
    turn = TurnOrchestrator(factory, claude).run_opening(sid, Events())
    assert turn.seq == 0 and turn.status == "committed"
    assert "opening scene" in final_user_message(claude)


def test_a_stall_nudge_names_a_clue_on_the_8th_turn_and_repeats(factory, story_world):
    sid = story_world()
    claude = FakeClaude(*[text(f"Nothing happens {i}.") for i in range(10)])
    orch = TurnOrchestrator(factory, claude)
    for i in range(10):
        orch.run_turn(sid, f"I wait {i}", Events())
    stalls = ["STALL" in final_user_message(claude, i) for i in range(10)]
    assert stalls == [False] * 8 + [True, True]  # Turn seq 8 is 8 Turns after the last progress at Turn 0
    msg = final_user_message(claude, 8)
    assert "Turns since progress: 8" in msg
    assert "Bring Clue clue.sluice.1 (Wet footprints lead from the mill's waterwheel" in msg  # from another Location


def test_play_stops_at_defeat_even_when_claude_skips_end_campaign(factory, story_world):
    sid = story_world()
    claude = FakeClaude(tool("tick_clock", clock="clock.tide", segments=3, reason="delay"), text("The tide creeps."),
                        tool("tick_clock", clock="clock.tide", segments=3, reason="delay"), text("The bell tolls."))
    orch = TurnOrchestrator(factory, claude)
    orch.run_turn(sid, "I nap", Events())
    ev = Events()
    orch.run_turn(sid, "I nap again", ev)
    assert ev[-3:] == [("state_changed", {"turn_seq": 1}), ("turn_done", {"turn_seq": 1}),
                       ("campaign_ended", {"campaign_id": 1, "ending": "defeat"})]
    camp = campaign(factory, sid)
    assert (camp.status, camp.ending) == ("complete", "defeat")
    with pytest.raises(CampaignEnded):
        orch.run_turn(sid, "I keep going", Events())
    assert len(claude.requests) == 4 and len(turns(factory, sid)) == 2


def test_a_failed_turn_leaves_the_story_unchanged(factory, story_world):
    sid = story_world()
    claude = FakeClaude([tool("reveal_clue", clue="clue.sluice.3"), tool("move_to", location="loc.mill")],
                        ClaudeError("overloaded"))
    turn = TurnOrchestrator(factory, claude).run_turn(sid, "I search the shore", Events())
    assert turn.status == "failed"
    camp = campaign(factory, sid)
    assert camp.current_location == "loc.shore" and camp.secrets[0].learned_turn is None
    assert all(c.revealed_turn is None for s in camp.secrets for c in s.clues)


def test_m3_exit_one_shot_from_opening_hook_to_victory(factory, story_world):
    """M3 exit: the one-shot fixture played from its opening scene to a Victory, with scripted Claude."""
    sid = story_world("rogue")
    claude = FakeClaude(
        text("Fog on the Reed Shore. A hooded figure runs. What do you do?"),
        tool("reveal_clue", clue="clue.sluice.3"), text("The map marks the mill."),
        [tool("move_to", location="loc.village"), tool("reveal_clue", clue="clue.rope.1")], text("Mira's story chills you."),
        tool("advance_beat", beat="act1.ferryman", outcome="Osric is held in the undercroft."), text("Hesta knows."),
        [tool("move_to", location="loc.mill"), tool("advance_beat", beat="act1.undercroft", outcome="Through the sluice.")],
        text("You wade into the dark."),
        [tool("move_to", location="loc.chapel"), tool("advance_beat", beat="act1.bell", outcome="The rope is cut with silver.")],
        tool("end_campaign", ending="victory"),
        text("The bell falls silent. Marrowford wakes to a clear dawn."),
    )
    orch = TurnOrchestrator(factory, claude)
    ev = Events()
    orch.run_opening(sid, ev)
    for action in ("I chase the figure", "I ask in the village", "I ask Hesta about Osric", "I enter the sluice",
                   "I climb the bell tower and cut the rope"):
        orch.run_turn(sid, action, ev)
    assert "error" not in ev.kinds() and ev[-1] == ("campaign_ended", {"campaign_id": 1, "ending": "victory"})
    # advance_beat told Claude the Victory condition was met before it called end_campaign.
    assert "victory_condition_met" in str(claude.requests[-2]["messages"][-1]["content"])
    camp = campaign(factory, sid)
    assert (camp.status, camp.ending, camp.current_location) == ("complete", "victory", "loc.chapel")
    assert [b.resolved_turn for b in camp.beats] == [3, 4, 5]
    assert [s.learned_turn for s in camp.secrets] == [1, 2]
    with pytest.raises(CampaignEnded):
        orch.run_turn(sid, "I ring the bell anyway", Events())


def test_m3_exit_an_idle_player_is_brought_a_clue_within_8_turns(factory, story_world):
    """M3 exit: a player who does nothing still gets a Clue by Turn 8, because the Stall nudge names one."""
    sid = story_world()

    class Director(FakeClaude):
        """Plays the idle Turns, and on a Stall reveals the Clue the nudge names."""

        def send(self, **kw):
            content = kw["messages"][-1]["content"]
            msg = content[0].get("text", "") if isinstance(content, list) else content
            if "STALL" in msg:
                slug = msg.split("Bring Clue ")[1].split(" ")[0]
                self.script = [tool("reveal_clue", clue=slug), text("A messenger staggers in with a map.")]
            elif not self.script:
                self.script = [text("The fog hangs still.")]
            return super().send(**kw)

    orch = TurnOrchestrator(factory, Director())
    orch.run_opening(sid, Events())
    for _ in range(8):
        orch.run_turn(sid, "I wait", Events())
    revealed = [c for s in campaign(factory, sid).secrets for c in s.clues if c.revealed_turn is not None]
    assert [(c.slug, c.revealed_turn) for c in revealed] == [("clue.sluice.1", 8)]


# --- M4: Sessions, Recaps, caching and the token budget --------------------------------------

def next_session(factory, session_id, rolling="", final="", current_rolling=""):
    """Close a Session with the given Recaps and open the Campaign's next one."""
    from datetime import datetime, timezone
    with factory() as db:
        old = db.get(Session, session_id)
        old.ended_at, old.rolling_recap, old.final_recap = datetime.now(timezone.utc), rolling, final
        new = Session(campaign_id=old.campaign_id, rolling_recap=current_rolling)
        db.add(new)
        db.commit()
        return new.id


def recap_of(msg):
    return msg[msg.index("<recap>"):msg.index("</recap>")]


def test_cache_breakpoints_sit_on_the_last_system_block_and_the_final_user_message(factory, story_world):
    sid = story_world()
    claude = FakeClaude(tool("roll", expr="1d4", purpose="luck"), text("The die settles."))
    TurnOrchestrator(factory, claude, rng=scripted_rng([2])).run_turn(sid, "I roll", Events())
    for req in claude.requests:
        assert req["system"][-1]["cache_control"] == {"type": "ephemeral"}
        assert all("cache_control" not in b for b in req["system"][:-1])
    first, second = claude.requests[0]["messages"], claude.requests[1]["messages"]
    assert first[-1]["content"][-1]["cache_control"] == {"type": "ephemeral"}
    # The Tool round rereads the marked message from the cache; nothing after it carries a marker.
    assert second[len(first) - 1] == first[-1]
    assert "cache_control" not in str(second[len(first):])


def test_turn_seq_and_history_continue_across_sessions(factory, world):
    sid = world()
    orch = TurnOrchestrator(factory, FakeClaude(text("One."), text("Two."), text("Three.")))
    orch.run_turn(sid, "a", Events())
    orch.run_turn(sid, "b", Events())
    sid2 = next_session(factory, sid)
    turn = orch.run_turn(sid2, "c", Events())
    assert (turn.seq, turn.session_id) == (2, sid2)
    msgs = orch.client.requests[2]["messages"]
    assert [(m["role"], m["content"]) for m in msgs[:-1]] == [
        ("user", "a"), ("assistant", "One."), ("user", "b"), ("assistant", "Two.")]


def test_the_recap_block_carries_the_previous_final_recap_and_this_sessions_rolling_recap(factory, story_world):
    sid = story_world()
    sid2 = next_session(factory, sid, rolling="You waded the reeds.", final="You found the mill.",
                        current_rolling="Tonight you met Hesta.")
    claude = FakeClaude(text("Fog."))
    TurnOrchestrator(factory, claude).run_turn(sid2, "I look around", Events())
    msg = final_user_message(claude)
    recap = recap_of(msg)
    assert "You found the mill." in recap and "Tonight you met Hesta." in recap
    assert "You waded the reeds." not in recap
    assert msg.index("</director>") < msg.index("<recap>") < msg.index("Player action: I look around")


def test_a_missing_final_recap_falls_back_to_the_previous_rolling_recap(factory, story_world):
    sid = story_world()
    sid2 = next_session(factory, sid, rolling="You waded the reeds.", final="")
    claude = FakeClaude(text("Fog."))
    TurnOrchestrator(factory, claude).run_turn(sid2, "I look around", Events())
    assert "You waded the reeds." in recap_of(final_user_message(claude))


def test_the_first_session_has_no_recap_block(factory, story_world):
    claude = FakeClaude(text("Fog."))
    TurnOrchestrator(factory, claude).run_turn(story_world(), "I look around", Events())
    assert "<recap>" not in final_user_message(claude)


def test_a_later_session_opens_with_a_resume_turn(factory, story_world):
    sid = story_world()
    orch = TurnOrchestrator(factory, FakeClaude(text("Fog on the Reed Shore."), text("Previously... What do you do?")))
    orch.run_opening(sid, Events())
    sid2 = next_session(factory, sid, final="You reached the shore.")
    turn = orch.run_resume(sid2, Events())
    assert (turn.seq, turn.status) == (1, "committed")
    msg = final_user_message(orch.client, 1)
    assert "You reached the shore." in recap_of(msg)
    action = msg[msg.index("Player action:"):]
    assert "previously" in action and "where the Character stands" in action and "question" in action


def test_a_stall_begun_in_session_1_is_detected_in_session_2(factory, story_world):
    sid = story_world()
    claude = FakeClaude(*[text(f"Fog {i}.") for i in range(9)])
    orch = TurnOrchestrator(factory, claude)
    for i in range(5):
        orch.run_turn(sid, f"I wait {i}", Events())     # seq 0 to 4
    sid2 = next_session(factory, sid)
    for i in range(4):
        orch.run_turn(sid2, f"I wait {i}", Events())    # seq 5 to 8
    assert ["STALL" in final_user_message(claude, i) for i in range(9)] == [False] * 8 + [True]


def test_the_budget_drops_the_oldest_history_pairs_but_never_the_snapshot_director_or_recap(factory, story_world):
    sid = story_world()
    sid2 = next_session(factory, sid, final="You found the mill.")
    big = "x" * 40000  # about 10,000 tokens at 4 characters per token
    claude = FakeClaude(text(big), text(big), text(big), text("ok"))
    orch = TurnOrchestrator(factory, claude, context_budget=15000)
    for action in ("a", "b", "c", "d"):
        orch.run_turn(sid2, action, Events())
    msgs = claude.requests[3]["messages"]
    assert [m["content"] for m in msgs[:-1]] == ["c", big]  # one pair fits next to the context; two do not
    msg = final_user_message(claude, 3)
    assert "<state>" in msg and "<director>" in msg and "You found the mill." in recap_of(msg)
    # With the default budget of 8,000 tokens no such pair fits at all.
    TurnOrchestrator(factory, FakeClaude(text("ok"))).run_turn(sid2, "e", Events())
