"""Seam 2: the turn orchestrator with a scripted fake Claude client and an event collector."""

from __future__ import annotations

import copy
import itertools

import pytest
from sqlalchemy import select

from pidm.claude import ClaudeError, Reply, Usage
from pidm.engine import load_state
from pidm.models import Campaign, RollRecord, Session, Turn
from pidm.orchestrator import TurnAlreadyRunning, TurnOrchestrator
from pidm.templates import create_character

_ids = itertools.count(1)


def tool(name, **args):
    return {"type": "tool_use", "id": f"toolu_{next(_ids)}", "name": name, "input": args}


def text(t):
    return {"type": "text", "text": t}


class FakeClaude:
    """Returns scripted replies in order; an Exception in the script is raised instead."""

    def __init__(self, *script):
        self.script = list(script)
        self.requests = []

    def send(self, *, system, messages, tools, tools_enabled, on_text):
        self.requests.append({"system": system, "messages": copy.deepcopy(messages), "tools_enabled": tools_enabled})
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        blocks = item if isinstance(item, list) else [item]
        if on_text:
            for b in blocks:
                if b["type"] == "text":
                    on_text(b["text"])
        stop = "tool_use" if any(b["type"] == "tool_use" for b in blocks) else "end_turn"
        return Reply(content=blocks, stop_reason=stop, usage=Usage(100, 20, 60))


class Events(list):
    def __call__(self, event, payload):
        self.append((event, payload))

    def kinds(self):
        return [e for e, _ in self]


def scripted_rng(values):
    it = iter(values)
    return lambda sides: next(it)


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
    assert ev.kinds() == ["roll", "narration_delta", "turn_done"]
    assert ev[0][1]["total"] == 4 and ev[1][1]["text"] == "Flames lick your boots."
    assert turn.status == "committed" and turn.seq == 0
    assert (turn.tokens_in, turn.tokens_out, turn.tokens_cached) == (200, 40, 120)
    assert character(factory, sid).hp_current == 8
    with factory() as db:
        rolls = db.scalars(select(RollRecord)).all()
        assert [(r.purpose, r.total) for r in rolls] == [("Bram takes fire damage", 4)]
    # The request carried the state snapshot and the player's action in the final user message.
    first = claude.requests[0]["messages"][-1]["content"]
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
    assert [p["text"] for e, p in ev if e == "narration_delta"] == ["The die settles."]


def test_tool_round_cap_forces_a_narration_only_call(factory, world):
    sid = world()
    rounds = [tool("roll", expr="1d4", purpose=f"r{i}") for i in range(4)]
    claude = FakeClaude(*rounds, text("Enough dice."))
    ev = Events()
    turn = TurnOrchestrator(factory, claude, round_cap=4, rng=scripted_rng([1, 2, 3, 4])).run_turn(sid, "x", ev)
    assert [r["tools_enabled"] for r in claude.requests] == [True, True, True, True, False]
    assert turn.narration == "Enough dice." and turn.status == "committed"
    assert ev.kinds()[-2:] == ["narration_delta", "turn_done"]


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
