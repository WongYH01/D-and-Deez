"""M6a: Scenes end by `end_scene` or after 15 Turns, and each finished Scene gets a background summary."""

from __future__ import annotations

from sqlalchemy import select

from pidm.claude import ClaudeError
from pidm.models import Scene

from conftest import text, tool
from test_server import act, create, make_server, server, start  # noqa: F401 (fixtures)


def scenes(factory) -> list[Scene]:
    with factory() as db:
        return list(db.scalars(select(Scene).order_by(Scene.id)))


def test_end_scene_records_the_scene_through_this_turn(make_game):
    g = make_game("fighter")
    g.state.turn = 3
    assert g.ok("end_scene", reason="left the tavern") == {"ended": True, "reason": "left the tavern"}
    g.commit()
    assert [(s.start_turn, s.end_turn, s.summary) for s in g.db.scalars(select(Scene))] == [(0, 3, "")]


def test_end_scene_twice_in_one_turn_is_an_error(make_game):
    g = make_game("fighter")
    g.ok("end_scene", reason="a")
    assert "already ended" in g.call("end_scene", reason="b")["error"]


def test_end_scene_is_refused_during_an_encounter(make_game):
    g = make_game("fighter")
    g.script(10, 10, 10).ok("start_encounter", monsters=[{"monster": "goblin", "count": 1}])
    assert "Encounter" in g.call("end_scene", reason="x")["error"]
    assert g.db.scalars(select(Scene)).all() == []


def test_a_played_session_has_scenes_with_summaries(factory, server):
    sid = start(server, create(server))  # Turn 0
    server.recap.script.append(text("You left the shore."))
    act(server, "I leave", [tool("end_scene", reason="change of place")], text("The path winds on."))  # Turn 1
    assert [(s.start_turn, s.end_turn, s.summary) for s in scenes(factory)] == [(0, 1, "You left the shore.")]
    assert "I leave" in server.recap.requests[0]["messages"][0]["content"]
    # The next Scene runs out after 15 Turns without end_scene: Turns 2 to 16.
    for i in range(14):
        act(server, f"I wait {i}")
    assert len(scenes(factory)) == 1
    server.recap.script.append(text("Fifteen quiet Turns."))
    act(server, "I wait again")
    assert [(s.start_turn, s.end_turn, s.session_id) for s in scenes(factory)][1:] == [(2, 16, sid)]
    assert scenes(factory)[1].summary


def test_a_failed_summary_leaves_play_unaffected(factory, server):
    start(server, create(server))
    server.recap.script.append(ClaudeError("down"))
    r = act(server, "I leave", [tool("end_scene", reason="x")], text("On."))
    assert r.status_code == 202 and server.events[-1][0] == "turn_done"
    assert [s.summary for s in scenes(factory)] == [""]
    assert act(server, "I wait").status_code == 202


def test_a_scene_is_not_auto_ended_during_an_encounter(make_game):
    from pidm.scenes import end_overlong_scene
    g = make_game("fighter")
    g.script(10, 10, 10).ok("start_encounter", monsters=[{"monster": "goblin", "count": 1}])
    g.state.turn = 20
    end_overlong_scene(g.state)
    assert g.db.scalars(select(Scene)).all() == []
