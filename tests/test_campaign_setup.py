"""Seam 3: Campaign setup with a FakeClaude that returns Campaign bible tool calls."""

from __future__ import annotations

import pytest

from pidm.campaign import PLAN_TOOL, Setup, SetupError, start_campaign
from pidm.engine import load_state

from conftest import FakeClaude, fixture_bible, tool

SETUP = Setup(setting="dark fantasy", tone="grim", length="one-shot", lines="harm to children",
              veils="torture", hook="Raised by the ferryman Osric.\nOwes the marsh a debt.")


def bible_call(bible):
    return tool(PLAN_TOOL, **bible)


def story(factory, session_id):
    return load_state(factory(), session_id, None).campaign


def test_a_valid_bible_on_the_first_attempt_seeds_the_campaign(factory):
    claude = FakeClaude(bible_call(fixture_bible()))
    sess = start_campaign(factory, SETUP, "rogue", "Wren", client=claude)
    assert len(claude.requests) == 1
    req = claude.requests[0]
    assert req["force_tool"] == PLAN_TOOL and [t["name"] for t in req["tools"]] == [PLAN_TOOL]
    prompt = req["messages"][0]["content"]
    assert "dark fantasy" in prompt and "Raised by the ferryman Osric." in prompt and "harm to children" in prompt

    camp = story(factory, sess.id)
    assert camp.name == "The Drowned Bell" and camp.premise.startswith("Fishermen in the marsh village")
    assert (camp.setting, camp.tone, camp.length, camp.lines, camp.veils) == (
        "dark fantasy", "grim", "one-shot", "harm to children", "torture")
    assert (camp.current_act, camp.current_location, camp.status, camp.ending) == (1, "loc.shore", "active", None)
    assert camp.character.name == "Wren" and camp.character.char_class == "rogue"
    assert [(b.slug, b.act, b.requires, b.status) for b in camp.beats] == [
        ("act1.ferryman", 1, [], "open"),
        ("act1.undercroft", 1, ["secret.sluice"], "open"),
        ("act1.bell", 1, ["act1.undercroft", "secret.rope"], "open")]
    assert [(s.slug, s.act, [c.slug for c in s.clues]) for s in camp.secrets] == [
        ("secret.sluice", 1, ["clue.sluice.1", "clue.sluice.2", "clue.sluice.3"]),
        ("secret.rope", 1, ["clue.rope.1", "clue.rope.2", "clue.rope.3"])]
    assert camp.secrets[0].clues[0].location == "loc.mill"
    assert [(c.slug, c.segments, c.filled, c.is_main) for c in camp.clocks] == [
        ("clock.tide", 6, 0, True), ("clock.suspicion", 4, 0, False)]


def test_an_invalid_bible_is_regenerated_with_the_errors_fed_back(factory):
    broken = fixture_bible()
    broken["clues"] = [c for c in broken["clues"] if c["slug"] != "clue.rope.3"]
    claude = FakeClaude(bible_call(broken), bible_call(fixture_bible()))
    sess = start_campaign(factory, SETUP, "fighter", None, client=claude)
    assert len(claude.requests) == 2
    assert all(r["force_tool"] == PLAN_TOOL for r in claude.requests)
    retry = str(claude.requests[1]["messages"][-1]["content"])
    assert "Secret secret.rope has 2 Clues" in retry
    assert story(factory, sess.id).name == "The Drowned Bell"


def test_every_tool_call_in_a_rejected_reply_gets_a_tool_result(factory):
    broken = fixture_bible()
    broken["clues"] = [c for c in broken["clues"] if c["slug"] != "clue.rope.3"]
    first, second = bible_call(broken), bible_call(broken)
    claude = FakeClaude([first, second], bible_call(fixture_bible()))
    start_campaign(factory, SETUP, "fighter", None, client=claude)
    results = claude.requests[1]["messages"][-1]["content"]
    assert [r["tool_use_id"] for r in results] == [first["id"], second["id"]]


def test_three_failed_attempts_raise_a_setup_error(factory):
    broken = fixture_bible()
    broken["clocks"][1]["main"] = True
    claude = FakeClaude(*[bible_call(broken) for _ in range(3)])
    with pytest.raises(SetupError, match="exactly one Main clock"):
        start_campaign(factory, SETUP, "fighter", None, client=claude)
    assert len(claude.requests) == 3


def test_a_ready_bible_makes_no_claude_call(factory):
    claude = FakeClaude()
    sess = start_campaign(factory, SETUP, "barbarian", None, client=claude, bible=fixture_bible())
    assert claude.requests == []
    camp = story(factory, sess.id)
    assert camp.bible["title"] == "The Drowned Bell" and len(camp.beats) == 3


def test_a_visible_clock_other_than_the_main_clock_passes_and_is_seeded_visible(factory):
    b = fixture_bible()
    b["clocks"][1]["visible"] = True
    sess = start_campaign(factory, SETUP, "fighter", None, bible=b)
    assert [(c.slug, c.visible) for c in story(factory, sess.id).clocks] == [
        ("clock.tide", False), ("clock.suspicion", True)]


def _two_clues(b):
    b["clues"] = [c for c in b["clues"] if c["slug"] != "clue.sluice.3"]


def _one_location(b):
    for c in b["clues"]:
        if c["secret"] == "secret.sluice":
            c["location"] = "loc.mill"


def _dangling(b):
    b["clues"][0]["location"] = "loc.nowhere"


def _two_mains(b):
    b["clocks"][1]["main"] = True


def _no_defeat(b):
    del b["endings"]["defeat"]


@pytest.mark.parametrize("break_it, length, error", [
    (_two_clues, "one-shot", "Secret secret.sluice has 2 Clues"),
    (_one_location, "one-shot", "Clues of Secret secret.sluice are not spread over at least 2 Locations"),
    (_dangling, "one-shot", "Clue clue.sluice.1 is placed in Location 'loc.nowhere'"),
    (lambda b: None, "short", "A short needs 3 Act(s); the bible has 1"),
    (_two_mains, "one-shot", "exactly one Main clock; it has 2"),
    (lambda b: b["clocks"][0].update(visible=True), "one-shot", "Main clock clock.tide is visible"),
    (_no_defeat, "one-shot", "endings.defeat: Field required"),
])
def test_a_broken_bible_is_rejected(factory, break_it, length, error):
    b = fixture_bible()
    break_it(b)
    setup = Setup(setting="high fantasy", tone="heroic", length=length)
    with pytest.raises(SetupError, match=error.replace("(", r"\(").replace(")", r"\)")):
        start_campaign(factory, setup, "fighter", None, bible=b)
