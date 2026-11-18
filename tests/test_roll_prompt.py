"""Roll prompts: Seam 1 (which tool calls ask the player) and Seam 2 (the Turn pauses until the player clicks Roll).

Numbers: Fighter Bram Str 16 (longsword +5, damage 1d8+3), Perception +3, Dex save +2; Goblin AC 15.
"""

from __future__ import annotations

import threading
import time

from pidm.models import Campaign
from pidm.orchestrator import TurnOrchestrator

from conftest import Events, FakeClaude, scripted_rng, set_auto_roll, text, tool
from test_combat import fight
from test_orchestrator import world  # noqa: F401  (fixture)


def watch(g):
    """Record each prompt with the number of Rolls already made when it was asked."""
    asked = []
    g.dice.prompt = lambda info: asked.append((info, len(g.dice.rolls)))
    return asked


# --- Seam 1 -------------------------------------------------------------------------------------

def test_a_skill_check_asks_once_before_it_rolls(make_game):
    g = make_game("fighter")
    asked = watch(g)
    g.script(12, 5).ok("skill_check", skill="perception", dc=12, advantage=True)
    assert asked == [({"purpose": "Bram perception check", "bonus": 3, "target": 12, "versus": None,
                       "mode": "advantage"}, 0)]


def test_a_character_save_asks_but_a_monster_save_never_does(make_game):
    g = make_game("fighter")
    fight(g, "goblin")
    asked = watch(g)
    g.script(10).ok("saving_throw", target="Goblin 1", ability="dex", dc=12)
    assert asked == []
    g.script(10).ok("saving_throw", target="character", ability="dex", dc=12)
    assert [(a["purpose"], a["bonus"], a["target"]) for a, _ in asked] == [("Bram DEX saving throw", 2, 12)]


def test_an_attack_asks_once_and_rolls_hit_and_damage_together(make_game):
    g = make_game("fighter")
    fight(g, "goblin")
    asked, before = watch(g), len(g.dice.rolls)
    g.script(15, 4).ok("attack", target="Goblin 1", weapon="longsword")
    assert len(asked) == 1 and asked[0][1] == before and asked[0][0]["target"] is None and asked[0][0]["versus"] == "Goblin 1" and asked[0][0]["bonus"] == 5
    assert len(g.last_rolls) == 2  # the hit and the damage


def test_a_contest_asks_once_for_the_characters_side(make_game):
    g = make_game("fighter")
    fight(g, "goblin")
    asked = watch(g)
    g.script(12, 9).ok("contest", a="character", b="Goblin 1", skill_a="athletics", skill_b="acrobatics")
    assert [(a["purpose"], a["versus"], a["target"]) for a, _ in asked] == [
        ("Bram athletics (contest)", "Goblin 1", None)]


def test_monster_turns_and_damage_rolls_never_ask(make_game):
    g = make_game("fighter")
    fight(g, "goblin", char_init=1, monster_inits=[20])
    asked = watch(g)
    g.script(15, 4, 3).ok("resolve_npc_turns")  # the goblin's attack roll and damage roll
    assert asked == [] and g.last_rolls


# --- Seam 2 -------------------------------------------------------------------------------------

def play(orch, sid, action, ev):
    """Run a Turn on a thread, as the server does, so the test can answer its prompt."""
    t = threading.Thread(target=orch.run_turn, args=(sid, action, ev))
    t.start()
    return t


def wait_for(ev, kind, timeout=5):
    end = time.time() + timeout
    while kind not in ev.kinds():
        assert time.time() < end, f"no {kind} in {ev.kinds()}"
        time.sleep(0.01)


def test_the_turn_pauses_at_a_roll_prompt_until_the_player_answers(factory, world):  # noqa: F811
    sid = world()
    set_auto_roll(factory, False)
    claude = FakeClaude(tool("skill_check", skill="perception", dc=12), text("You spot a tripwire."))
    ev = Events()
    orch = TurnOrchestrator(factory, claude, rng=scripted_rng([12]))
    t = play(orch, sid, "I look around", ev)
    wait_for(ev, "roll_prompt")
    time.sleep(0.1)
    assert ev.kinds() == ["roll_prompt"] and len(claude.requests) == 1  # nothing rolled, no Narration yet
    assert orch.pending == ev[0][1] and orch.pending["n"] == 0
    assert ev[0][1] == {"turn_seq": 0, "n": 0, "purpose": "Bram perception check", "bonus": 3, "target": 12,
                        "versus": None, "mode": "normal"}
    assert orch.answer_roll(0, 0)
    t.join(5)
    assert ev.kinds() == ["roll_prompt", "roll", "narration_delta", "state_changed", "turn_done"]
    assert ev[1][1]["total"] == 15 and ev[1][1]["answers_prompt"] == 0
    assert orch.pending is None and not orch.answer_roll()


def test_auto_roll_skips_the_prompt(factory, world):  # noqa: F811
    sid = world()  # Auto-roll is on in tests unless a test turns it off
    claude = FakeClaude(tool("skill_check", skill="perception", dc=12), text("Nothing."))
    ev = Events()
    TurnOrchestrator(factory, claude, rng=scripted_rng([12])).run_turn(sid, "look", ev)
    assert ev.kinds() == ["roll", "narration_delta", "state_changed", "turn_done"]


def test_an_unanswered_prompt_auto_rolls_after_the_timeout(factory, world):  # noqa: F811
    sid = world()
    set_auto_roll(factory, False)
    claude = FakeClaude(tool("skill_check", skill="perception", dc=12), text("Nothing."))
    ev = Events()
    TurnOrchestrator(factory, claude, rng=scripted_rng([12]), prompt_timeout=0.05).run_turn(sid, "look", ev)
    assert ev.kinds() == ["roll_prompt", "roll", "narration_delta", "state_changed", "turn_done"]


def test_a_failed_turn_clears_the_pending_prompt(factory, world):  # noqa: F811
    sid = world()
    set_auto_roll(factory, False)
    claude = FakeClaude(tool("skill_check", skill="perception", dc=12), RuntimeError("boom"))
    ev = Events()
    orch = TurnOrchestrator(factory, claude, rng=scripted_rng([12]), prompt_timeout=0.05)
    orch.run_turn(sid, "look", ev)
    assert ev.kinds()[-1] == "error" and orch.pending is None
