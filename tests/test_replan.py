"""Between-session replanning through the server (Seam 4): the replan job, bible versions and rollback."""

from __future__ import annotations

import copy

import pytest
from sqlalchemy import select

from d_and_deez.bible import Bible
from d_and_deez.claude import ClaudeError
from d_and_deez.models import BibleVersion, Campaign
from d_and_deez.replan import REPLAN_TOOL, rollback

from conftest import act, campaigns, create, fixture_bible, start, text, tool


def original() -> dict:
    """The fixture bible as a saved bible holds it, with every default filled in."""
    return Bible.model_validate(fixture_bible()).model_dump()


def proposal(edit) -> dict:
    b = fixture_bible()
    edit(b)
    return tool(REPLAN_TOOL, **b)


def move_clue(b, slug="clue.sluice.1", to="loc.chapel"):
    next(c for c in b["clues"] if c["slug"] == slug)["location"] = to


def play_and_end(s, *replies):
    cid = create(s)
    start(s, cid)
    for r in replies:
        act(s, "look", *r)
    s.recap.script.append(text("You looked around."))
    return cid


def versions(factory, cid):
    with factory() as db:
        camp = db.get(Campaign, cid)
        return [(v.version, v.diff) for v in camp.bible_versions], camp.bible


def clue_rows(factory, cid):
    with factory() as db:
        return {c.slug: (c.location, c.revealed_turn) for s in db.get(Campaign, cid).secrets for c in s.clues}


def test_a_session_end_replans_and_saves_a_new_version(factory, server):
    cid = play_and_end(server, [text("Nothing.")])
    server.plan.script.append(proposal(move_clue))
    server.http.post("/session/end")
    vs, bible = versions(factory, cid)
    assert [v for v, _ in vs] == [1, 2]
    assert "clue.sluice.1" in vs[1][1] and "loc.chapel" in vs[1][1]
    assert next(c for c in bible["clues"] if c["slug"] == "clue.sluice.1")["location"] == "loc.chapel"
    assert clue_rows(factory, cid)["clue.sluice.1"][0] == "loc.chapel"  # play uses the latest version
    assert REPLAN_TOOL == server.plan.requests[-1]["force_tool"]
    assert "Facts of the world" in server.plan.requests[-1]["messages"][0]["content"]


def test_the_ui_sees_only_a_flag_never_the_diff(factory, server):
    cid = play_and_end(server, [text("Nothing.")])
    assert campaigns(server)[cid]["adapted"] is False
    server.plan.script.append(proposal(move_clue))
    server.http.post("/session/end")
    row = campaigns(server)[cid]
    assert row["adapted"] is True
    assert "loc.chapel" not in str(row) and "clue.sluice" not in str(row)


def test_played_content_cannot_be_changed_by_a_proposal(factory, server):
    cid = play_and_end(server, [tool("reveal_clue", clue="clue.sluice.1"), text("A note by the sluice.")],
                       [tool("advance_beat", beat="act1.ferryman", outcome="Osric is found."), text("Found.")])

    def meddle(b):
        move_clue(b)  # a revealed Clue
        b["acts"][0]["beats"][0]["goal"] = "Something else"  # a resolved Beat
        b["endings"]["victory"] = "Changed"
        b["secrets"][0]["revelation"] = "Changed"
        next(c for c in b["clocks"] if c["main"])["segments"] = 12
        next(c for c in b["clues"] if c["slug"] == "clue.rope.1")["location"] = "loc.chapel"  # unplayed: allowed

    server.plan.script.append(proposal(meddle))
    server.http.post("/session/end")
    _, bible = versions(factory, cid)
    old = original()
    assert bible["acts"][0]["beats"][0] == old["acts"][0]["beats"][0]
    assert bible["endings"] == old["endings"] and bible["secrets"] == old["secrets"]
    assert next(c for c in bible["clocks"] if c["main"]) == next(c for c in old["clocks"] if c["main"])
    rows = clue_rows(factory, cid)
    assert rows["clue.sluice.1"][0] == "loc.mill" and rows["clue.sluice.1"][1] is not None
    assert rows["clue.rope.1"][0] == "loc.chapel"


def test_an_invalid_proposal_is_retried_with_the_errors_then_dropped(factory, server):
    cid = play_and_end(server, [text("Nothing.")])
    bad = proposal(lambda b: b["clues"].remove(next(c for c in b["clues"] if c["slug"] == "clue.sluice.1")))
    server.plan.script.extend([bad, bad, bad])
    server.http.post("/session/end")
    assert [v for v, _ in versions(factory, cid)[0]] == [1]
    assert len(server.plan.requests) == 1 + 3  # the bible, then 3 attempts
    assert "Three Clue Rule" in str(server.plan.requests[2]["messages"][-1]["content"])
    assert len(list(server.backups.glob("*.sqlite"))) == 1  # the backup still runs


def test_a_failed_replan_keeps_the_version_and_a_no_change_adds_none(factory, server):
    cid = play_and_end(server, [text("Nothing.")])
    server.plan.script.append(ClaudeError("down"))
    server.http.post("/session/end")
    assert [v for v, _ in versions(factory, cid)[0]] == [1]
    server.plan.script.append(proposal(lambda b: None))
    start(server, cid)
    server.recap.script.append(text("Again."))
    act(server, "look")
    server.http.post("/session/end")
    assert [v for v, _ in versions(factory, cid)[0]] == [1]


def test_no_replan_for_a_session_without_turns_or_an_ended_campaign(factory, server):
    cid = create(server)
    start(server, cid)
    server.http.post("/session/end")
    start(server, cid)
    server.http.post(f"/campaigns/{cid}/retire")
    assert len(server.plan.requests) == 1  # the bible only


def test_the_next_session_opens_on_the_replanned_bible(factory, server):
    cid = play_and_end(server, [text("Nothing.")])
    server.plan.script.append(proposal(move_clue))
    server.http.post("/session/end")
    start(server, cid)
    assert '"location": "loc.chapel"' in str(server.turn.requests[-1]["system"])


def test_rollback_restores_an_earlier_version_as_a_new_one(factory, server):
    cid = play_and_end(server, [text("Nothing.")])
    server.plan.script.append(proposal(move_clue))
    server.http.post("/session/end")
    rollback(factory, cid, 1)
    vs, bible = versions(factory, cid)
    assert [v for v, _ in vs] == [1, 2, 3] and vs[2][1].startswith("Rolled back to version 1")
    old = original()
    assert {k: v for k, v in bible.items() if k not in ("clues", "clocks")} == {k: v for k, v in old.items() if k not in ("clues", "clocks")}
    assert sorted(bible["clues"], key=lambda c: c["slug"]) == sorted(old["clues"], key=lambda c: c["slug"])
    assert sorted(bible["clocks"], key=lambda c: c["slug"]) == sorted(old["clocks"], key=lambda c: c["slug"])
    assert clue_rows(factory, cid)["clue.sluice.1"][0] == "loc.mill"
    with pytest.raises(ValueError):
        rollback(factory, cid, 9)


def test_a_regenerated_campaign_starts_again_at_version_1(factory, server):
    cid = create(server)
    server.plan.script.append(tool("write_campaign_bible", **fixture_bible()))
    server.http.post(f"/campaigns/{cid}/regenerate")
    with factory() as db:
        assert [v.version for v in db.scalars(select(BibleVersion))] == [1]
