"""M6a: Scene recall with a local embedding model, and the v2 context-budget drop order (design: Memory strategy)."""

from __future__ import annotations

import logging

from sqlalchemy import select, text as sql

from d_and_deez.models import Scene
from d_and_deez.orchestrator import TurnOrchestrator
from d_and_deez.recall import embed_scene

from conftest import Events, FakeClaude, FakeEmbedder, act, create, fixture_bible, start, text, tool
from test_orchestrator import final_user_message, next_session


def add_scene(factory, session_id, start_turn, end_turn, summary, embedder):
    with factory() as db:
        scene = Scene(session_id=session_id, start_turn=start_turn, end_turn=end_turn, summary=summary)
        db.add(scene)
        db.commit()
        embed_scene(factory, embedder, scene.id)


def recall_of(msg):
    return msg[msg.index("<recall>"):msg.index("</recall>")] if "<recall>" in msg else ""


def test_an_npc_met_in_session_1_is_recalled_in_session_3_without_replaying_turns(factory, make_game):
    emb = FakeEmbedder()
    sid1 = make_game("fighter", fixture_bible()).session_id
    add_scene(factory, sid1, 0, 4, "You met Marrow the ferryman, who owes the Choir a debt.", emb)
    add_scene(factory, sid1, 5, 9, "You haggled over lamp oil in the market.", emb)
    add_scene(factory, sid1, 10, 14, "You slept badly in a damp inn.", emb)
    add_scene(factory, sid1, 15, 19, "You crossed the old bridge in heavy rain.", emb)
    sid3 = next_session(factory, next_session(factory, sid1))
    claude = FakeClaude(text("Marrow squints at you."))
    TurnOrchestrator(factory, claude, embedder=emb).run_turn(sid3, "I ask Marrow about his debt", Events())
    msg = final_user_message(claude)
    recalled = recall_of(msg)
    lines = recalled.splitlines()[1:]
    assert lines[0].startswith("- You met Marrow the ferryman")  # best first
    assert len(lines) == 3  # the top 3 of 4 Scenes
    assert len(claude.requests[0]["messages"]) == 1  # no old Turns replayed


def test_a_forced_embedder_failure_leaves_the_turn_successful_with_no_recall(factory, make_game, caplog):
    sid = make_game("fighter", fixture_bible()).session_id
    add_scene(factory, sid, 0, 4, "You met Marrow.", FakeEmbedder())
    claude = FakeClaude(text("Fog."))
    events = Events()
    with caplog.at_level(logging.WARNING):
        orch = TurnOrchestrator(factory, claude, embedder=FakeEmbedder(fail=RuntimeError("model gone")))
        turn = orch.run_turn(sid, "I ask Marrow", events)
    assert turn.status == "committed" and events.kinds()[-1] == "turn_done"
    assert "<recall>" not in final_user_message(claude)
    assert "recall" in caplog.text.lower()


def test_a_finished_scene_is_embedded_by_the_worker(factory, make_server):
    emb = FakeEmbedder()
    s = make_server(embedder=emb)
    start(s, create(s))
    s.recap.script.append(text("You left the shore."))
    act(s, "I leave", [tool("end_scene", reason="change of place")], text("On."))
    assert ["You left the shore."] in emb.calls
    # The next Turn recalls it.
    act(s, "I go back to the shore")
    assert "You left the shore." in recall_of(final_user_message(s.turn, -1))


def test_a_scene_whose_summary_failed_is_not_embedded(factory, make_server):
    emb = FakeEmbedder()
    s = make_server(embedder=emb)
    start(s, create(s))
    s.recap.script.append(RuntimeError("down"))
    act(s, "I leave", [tool("end_scene", reason="x")], text("On."))
    assert not any("leave" in c[0] for c in emb.calls[2:]) and "x" not in [c[0] for c in emb.calls]


def test_a_changed_model_id_re_embeds_scenes_at_startup(factory, make_server):
    sid = start(s := make_server(embedder=FakeEmbedder("model-a")), create(s))
    add_scene(factory, sid, 0, 1, "You left the shore.", FakeEmbedder("model-a"))
    newer = FakeEmbedder("model-b")
    make_server(embedder=newer)  # a restart with another configured model
    assert newer.calls == [["You left the shore."]]
    with factory() as db:
        assert db.scalars(sql("SELECT model_id FROM scene_vec")).all() == ["model-b"]
    again = FakeEmbedder("model-b")
    make_server(embedder=again)
    assert again.calls == []  # already current


def test_budget_drops_recall_and_far_facts_before_history_and_never_the_state_director_or_recap(factory, make_game):
    emb = FakeEmbedder()
    g = make_game("fighter", fixture_bible())
    g.ok("add_fact", subject="Old Hesta", relation="is grandmother of", object="Tam", subject_kind="npc", object_kind="npc")
    g.ok("add_fact", subject="Tam", relation="serves", object="The Choir", object_kind="faction")
    g.commit()
    sid = next_session(factory, g.session_id, final="You found the mill.")
    add_scene(factory, sid, 0, 3, "You met Marrow at the shore. " + "pad " * 2000, emb)  # about 2,000 tokens
    claude = FakeClaude(text("ok"), text("ok"), text("ok"), text("ok"))
    action = "I ask Old Hesta about Marrow"

    def play(budget):
        TurnOrchestrator(factory, claude, embedder=emb, context_budget=budget).run_turn(sid, action, Events())
        return final_user_message(claude, len(claude.requests) - 1), claude.requests[-1]["messages"]

    play(100000)  # puts one Turn in the history
    full, msgs = play(100000)
    assert "Marrow at the shore" in full and "Tam serves The Choir" in full and len(msgs) == 3
    size = len(full) // 4
    # Over budget by less than the recall: recall and the two-hop Fact go, one-hop Facts and history stay.
    cut, msgs = play(size - 500)
    assert "<recall>" not in cut and "Tam serves The Choir" not in cut
    assert "Old Hesta is grandmother of Tam" in cut and len(msgs) == 5
    # A tiny budget: history goes too, but never the snapshot, director block or recap.
    tiny, msgs = play(10)
    assert len(msgs) == 1
    assert "<state>" in tiny and "<director>" in tiny and "You found the mill." in tiny
