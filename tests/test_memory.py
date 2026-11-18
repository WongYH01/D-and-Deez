"""M6a: Entities, Facts and DM notes (design: Memory strategy)."""

from __future__ import annotations

from sqlalchemy import select

from pidm.memory import NOTE_CAP_CHARS
from pidm.models import DmNote, Entity, Fact

from conftest import act, create, fixture_bible, start, text, tool


def names(g) -> dict[str, str]:
    return {e.name: e.kind for e in g.db.scalars(select(Entity))}


def test_bible_npcs_and_locations_seed_entities(make_game):
    g = make_game("fighter", fixture_bible())
    got = names(g)
    assert got["Abbess Varn"] == "npc" and got["The abandoned tide mill"] == "place"
    assert len(got) == 3 + 4
    assert next(e for e in g.db.scalars(select(Entity)) if e.name.startswith("Mira")).aliases == ["Mira"]


def test_add_fact_creates_invented_entities_and_retire_sets_valid_to(make_game):
    g = make_game("fighter", fixture_bible())
    g.at_turn(4)
    r = g.ok("add_fact", subject="Mira", relation="works for", object="The Guild", object_kind="faction")
    assert names(g)["The Guild"] == "faction"  # Mira resolved by alias; no second Mira
    assert sum(e.name.startswith("Mira") for e in g.db.scalars(select(Entity))) == 1
    g.at_turn(9).ok("retire_fact", fact_id=r["fact_id"])
    g.commit()
    f = g.db.scalars(select(Fact)).one()
    assert (f.valid_from_turn, f.valid_to_turn, f.source_turn) == (4, 9, 4)


def test_invalid_fact_calls_change_nothing(make_game):
    g = make_game("fighter", fixture_bible())
    before = len(names(g))
    for args, why in [
        (dict(subject="Nobody", relation="knows", object="Old Hesta"), "subject_kind"),
        (dict(subject="Old Hesta", relation="", object="Abbess Varn"), "relation"),
        (dict(subject="Old Hesta", relation="is", object="Old Hesta"), "itself"),
        (dict(subject="Old Hesta", relation="x", object="Zed", object_kind="wizard"), "one of"),
    ]:
        assert why in g.call("add_fact", **args)["error"]
    assert "No Fact" in g.call("retire_fact", fact_id=99)["error"]
    g.commit()
    assert len(names(g)) == before and g.db.scalars(select(Fact)).all() == []


def test_duplicate_current_fact_and_double_retire_are_errors(make_game):
    g = make_game("fighter", fixture_bible())
    fid = g.ok("add_fact", subject="Old Hesta", relation="distrusts", object="Abbess Varn")["fact_id"]
    assert "already" in g.call("add_fact", subject="old hesta", relation="Distrusts", object="Abbess Varn")["error"]
    g.ok("retire_fact", fact_id=fid)
    assert "already retired" in g.call("retire_fact", fact_id=fid)["error"]


def test_note_cap_errors_until_an_older_note_is_updated_or_deleted(make_game):
    g = make_game("fighter")
    first = g.ok("write_note", note="x" * (NOTE_CAP_CHARS - 10))["note_id"]
    err = g.call("write_note", note="y" * 20)["error"]
    assert "cap" in err and str(first) in err
    assert len(g.state.campaign.dm_notes) == 1  # nothing was trimmed or added
    g.ok("write_note", note="short", note_id=first)  # update frees room
    second = g.ok("write_note", note="y" * 20)["note_id"]
    g.ok("write_note", note="", note_id=second)  # empty note deletes
    g.commit()
    assert [n.note for n in g.db.scalars(select(DmNote))] == ["short"]
    assert "No note" in g.call("write_note", note="z", note_id=99)["error"]


def test_context_has_facts_within_two_hops_and_all_notes(make_game):
    from pidm.memory import memory_blocks
    g = make_game("fighter", fixture_bible())
    g.ok("add_fact", subject="Old Hesta", relation="is grandmother of", object="Tam", subject_kind="npc", object_kind="npc")
    g.ok("add_fact", subject="Tam", relation="serves", object="The Choir", object_kind="faction")
    g.ok("add_fact", subject="The Choir", relation="meets in", object="The sunken chapel")
    g.ok("write_note", note="Player likes puns.")
    world, notes = memory_blocks(g.state, ["I ask Hesta about the tavern."])
    assert "Old Hesta is grandmother of Tam" in world and "Tam serves The Choir" in world
    assert "meets in" not in world  # three hops away
    assert "Player likes puns." in notes
    world1, _ = memory_blocks(g.state, ["I ask Hesta."], hops=1)
    assert "serves" not in world1


def test_current_location_entity_is_always_included(make_game):
    from pidm.memory import memory_blocks
    g = make_game("fighter", fixture_bible())
    g.ok("add_fact", subject="The Reed Shore", relation="is haunted by", object="A drowned ferryman", object_kind="npc")
    world, _ = memory_blocks(g.state, ["I look around."])  # start location is loc.shore
    assert "haunted" in world


def test_retired_facts_are_not_in_context(make_game):
    from pidm.memory import memory_blocks
    g = make_game("fighter", fixture_bible())
    fid = g.ok("add_fact", subject="Old Hesta", relation="distrusts", object="Abbess Varn")["fact_id"]
    g.ok("retire_fact", fact_id=fid)
    assert memory_blocks(g.state, ["Hesta"])[0] == ""


def test_npc_killed_in_one_session_is_dead_in_the_next(server):
    cid = create(server)
    start(server, cid)
    act(server, "I stab the abbess", [tool("add_fact", subject="Abbess Varn", relation="was killed by", object="Wren",
                                           object_kind="npc")], text("She falls."))
    server.recap.script.append(text("Final recap."))
    assert server.http.post("/session/end").status_code == 202
    server.turn.script.append(text("Previously..."))
    assert server.http.post("/session/start", json={"campaign_id": cid}).status_code == 202
    act(server, "I ask about Varn", [tool("write_note", note="Wren killed Varn.")], text("Nobody mentions her."))
    ctx = server.turn.requests[-2]["messages"][-1]["content"][0]["text"]
    assert "Abbess Varn was killed by Wren" in ctx
    act(server, "I wait")
    assert "<notes>" in server.turn.requests[-1]["messages"][-1]["content"][0]["text"]


def test_over_budget_context_drops_far_facts_before_history(factory):
    from pidm.campaign import Setup, start_campaign
    from pidm.orchestrator import TurnOrchestrator
    from conftest import Events, FakeClaude
    sid = start_campaign(factory, Setup("dark fantasy", "grim", "one-shot"), "fighter", None, bible=fixture_bible()).id
    claude = FakeClaude(
        text("ok"),  # Turn 0
        [tool("add_fact", subject="Old Hesta", relation="is grandmother of", object="Tam", subject_kind="npc",
              object_kind="npc"),
         tool("add_fact", subject="Tam", relation="serves", object="The Choir", object_kind="faction")],
        text("y" * 4000), text("ok"))
    orch = TurnOrchestrator(factory, claude)
    for action in ("begin", "set up the Facts", "I ask Hesta"):
        orch.run_turn(sid, action, Events())

    def context(c):
        return c.requests[-1]["messages"][-1]["content"][0]["text"]

    assert "serves The Choir" in context(claude)  # fits the default budget: two hops
    tight = FakeClaude(text("ok"))
    TurnOrchestrator(factory, tight, context_budget=900).run_turn(sid, "I ask Hesta", Events())
    assert "is grandmother of Tam" in context(tight) and "serves The Choir" not in context(tight)
