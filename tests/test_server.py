"""Seam 4: the FastAPI app built by `create_app` with FakeClaude clients, a temporary database and backups folder,
and inline work, driven through TestClient with a test subscriber on the broadcaster."""

from __future__ import annotations

import re
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
import uvicorn
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from pidm.app import create_app
from pidm.campaign import PLAN_TOOL
from pidm.claude import ClaudeError, Usage
from pidm.devclaude import DevClaude
from pidm.models import Campaign, Character, Combatant, Session, Turn

from conftest import Events, FakeClaude, fixture_bible, text, tool

SETUP = {"setting": "dark fantasy", "tone": "grim", "length": "one-shot", "template": "rogue",
         "character_name": "Wren", "hook": "Raised by the ferryman Osric.", "lines": "", "veils": ""}


def bible_call(bible=None):
    return tool(PLAN_TOOL, **(bible or fixture_bible()))


@pytest.fixture
def make_server(factory, tmp_path):
    def make(turn=(), plan=(), recap=(), web_dir=None):
        clients = SimpleNamespace(turn=FakeClaude(*turn), plan=FakeClaude(*plan), recap=FakeClaude(*recap))
        app = create_app(factory, turn_client=clients.turn, plan_client=clients.plan, recap_client=clients.recap,
                         backup_dir=tmp_path / "backups", inline=True, web_dir=web_dir)
        events = Events()
        app.state.broadcaster.subscribe(events)
        return SimpleNamespace(http=TestClient(app), events=events, backups=tmp_path / "backups", **vars(clients))
    return make


@pytest.fixture
def server(make_server):
    return make_server()


def create(s, **overrides) -> int:
    s.plan.script.append(bible_call())
    r = s.http.post("/campaigns", json={**SETUP, **overrides})
    assert r.status_code == 202
    return r.json()["campaign_id"]


def campaigns(s) -> dict[int, dict]:
    return {c["id"]: c for c in s.http.get("/campaigns").json()}


def start(s, campaign_id, narration="Fog on the Reed Shore. What do you do?") -> int:
    s.turn.script.append(text(narration))
    r = s.http.post("/session/start", json={"campaign_id": campaign_id})
    assert r.status_code == 202, r.text
    return r.json()["session_id"]


def act(s, action, *replies):
    s.turn.script.extend(replies or [text("Nothing stirs.")])
    return s.http.post("/action", json={"text": action})


def session_row(factory, session_id) -> Session:
    with factory() as db:
        return db.get(Session, session_id)


# --- Campaign setup -----------------------------------------------------------------------------

def test_a_new_campaign_is_generating_until_its_bible_is_saved_then_ready(server):
    seen = []

    class Planner(FakeClaude):
        def send(self, **kw):
            seen.append(campaigns(server))
            return super().send(**kw)

    server.plan.__class__ = Planner
    cid = create(server)
    assert seen[0][cid]["status"] == "generating" and seen[0][cid]["premise"] is None
    c = campaigns(server)[cid]
    assert (c["status"], c["name"], c["ending"], c["setup_error"]) == ("ready", "The Drowned Bell", None, "")
    assert c["premise"].startswith("Fishermen in the marsh village")
    assert "bible" not in c and "secret.rope" not in str(c)
    assert "Raised by the ferryman Osric." in server.plan.requests[0]["messages"][0]["content"]


def test_a_campaign_that_fails_three_validations_is_failed(make_server):
    broken = fixture_bible()
    broken["clocks"][1]["main"] = True
    s = make_server(plan=[bible_call(broken)] * 3)
    r = s.http.post("/campaigns", json=SETUP)
    c = campaigns(s)[r.json()["campaign_id"]]
    assert c["status"] == "failed" and "exactly one Main clock" in c["setup_error"]
    assert len(s.plan.requests) == 3


def test_a_campaign_generating_at_startup_is_failed(factory, make_server):
    with factory() as db:
        db.add(Campaign(name="", status="generating"))
        db.commit()
    c = campaigns(make_server())[1]
    assert c["status"] == "failed" and c["setup_error"]


def test_regenerate_replaces_a_ready_bible_on_the_same_campaign(factory, server):
    cid = create(server)
    renamed = fixture_bible()
    renamed["title"] = "The Silent Bell"
    server.plan.script.append(bible_call(renamed))
    assert server.http.post(f"/campaigns/{cid}/regenerate").status_code == 202
    assert [(c["id"], c["name"], c["status"]) for c in campaigns(server).values()] == [
        (cid, "The Silent Bell", "ready")]
    start(server, cid)
    assert server.http.get("/state").json()["character"]["name"] == "Wren"
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Character)) == 1  # the first Character is gone
    assert server.http.post(f"/campaigns/{cid}/regenerate").status_code == 409  # now active


# --- Sessions and Turns -------------------------------------------------------------------------

def test_session_start_accepts_the_premise_and_streams_the_opening_as_turn_0(server):
    cid = create(server)
    sid = start(server, cid)
    assert campaigns(server)[cid]["status"] == "active"
    assert server.events == [("narration_delta", {"turn_seq": 0, "text": "Fog on the Reed Shore. What do you do?"}),
                             ("state_changed", {"turn_seq": 0}), ("turn_done", {"turn_seq": 0})]
    assert "opening scene" in str(server.turn.requests[0]["messages"][-1]["content"])
    state = server.http.get("/state").json()
    assert (state["session_id"], state["campaign_id"], state["running_turn_seq"]) == (sid, cid, None)
    assert state["character"]["name"] == "Wren" and state["character"]["hp"] == 10


def test_an_action_streams_rolls_and_narration_then_commits(server):
    sid = start(server, create(server))
    server.events.clear()
    r = act(server, "I search the shore", tool("skill_check", skill="perception", dc=99), text("Only reeds."))
    assert r.status_code == 202 and r.json() == {"turn_seq": 1}
    assert server.events.kinds() == ["roll", "narration_delta", "state_changed", "turn_done"]
    assert all(p["turn_seq"] == 1 for _, p in server.events)
    assert server.events[0][1]["outcome"] == "failure" and server.events[0][1]["target"] == 99
    log = server.http.get(f"/log?session={sid}").json()
    assert [(t["seq"], t["player_text"], t["narration"]) for t in log][1] == (1, "I search the shore", "Only reeds.")
    assert [(r["purpose"], r["target"], r["outcome"]) for r in log[1]["rolls"]] == [
        ("Wren perception check", 99, "failure")]


def test_the_log_shows_no_player_text_for_opening_and_resume_turns(server):
    cid = create(server)
    sid1 = start(server, cid)
    server.recap.script.append(text("You landed on the Reed Shore."))
    server.http.post("/session/end")
    sid2 = start(server, cid, narration="Previously, you landed on the shore.")
    act(server, "I wade ashore")
    log1, log2 = (server.http.get(f"/log?session={s}").json() for s in (sid1, sid2))
    assert [t["player_text"] for t in log1 + log2] == ["", "", "I wade ashore"]


def test_a_failed_turn_changes_nothing_saves_a_failed_row_and_stays_out_of_the_log(factory, server):
    sid = start(server, create(server))
    before = server.http.get("/state").json()
    server.events.clear()
    r = act(server, "I touch the rune", tool("apply_damage", target="character", amount="5", damage_type="fire"),
            ClaudeError("overloaded", Usage(50, 0, 0)))
    assert r.status_code == 202
    assert server.events[-1][0] == "error" and server.events[-1][1]["retryable"]
    assert server.http.get("/state").json() == before
    assert [t["seq"] for t in server.http.get(f"/log?session={sid}").json()] == [0]
    with factory() as db:
        failed = db.scalar(select(Turn).where(Turn.status == "failed"))
        assert (failed.seq, failed.tokens_in, failed.tokens_out, failed.tokens_cached) == (1, 150, 20, 60)


def test_requests_during_a_running_turn_are_refused(server):
    cid = create(server)
    start(server, cid)
    seen = {}

    class Busy(FakeClaude):
        def send(self, **kw):
            if not seen:
                h = server.http
                seen["action"] = h.post("/action", json={"text": "again"}).status_code
                seen["end"] = h.post("/session/end").status_code
                seen["retire"] = h.post(f"/campaigns/{cid}/retire").status_code
                seen["start"] = h.post("/session/start", json={"campaign_id": cid}).status_code
                seen["equip"] = h.post("/inventory/1/unequip").status_code
                seen["running"] = h.get("/state").json()["running_turn_seq"]
            return super().send(**kw)

    server.turn.__class__ = Busy
    assert act(server, "I wait").status_code == 202
    assert seen == {"action": 409, "end": 409, "retire": 409, "start": 409, "equip": 409, "running": 1}
    assert server.http.get("/state").json()["running_turn_seq"] is None


def test_without_an_open_session_actions_are_refused_and_state_is_404(server):
    cid = create(server)
    assert server.http.post("/action", json={"text": "hello"}).status_code == 409
    assert server.http.get("/state").status_code == 404
    assert server.http.post("/session/end").status_code == 409
    assert server.http.post("/session/start", json={"campaign_id": 99}).status_code == 404
    assert server.http.post(f"/campaigns/{cid}/retire").status_code == 200  # a ready Campaign can be retired
    assert server.http.post("/session/start", json={"campaign_id": cid}).status_code == 409  # now complete


def test_session_end_writes_the_final_recap_and_a_backup(factory, server):
    sid = start(server, create(server))
    server.recap.script.append(text("You landed on the Reed Shore in the fog."))
    assert server.http.post("/session/end").status_code == 202
    assert server.http.get("/state").status_code == 404
    row = session_row(factory, sid)
    assert row.ended_at is not None and row.final_recap == "You landed on the Reed Shore in the fog."
    assert "Fog on the Reed Shore" in server.recap.requests[0]["messages"][0]["content"]
    assert len(list(server.backups.glob("*.sqlite"))) == 1


def test_session_start_writes_a_missing_final_recap_then_runs_a_resume_turn(factory, server):
    cid = create(server)
    sid1 = start(server, cid)
    server.recap.script.append(ClaudeError("overloaded"))
    server.http.post("/session/end")
    assert session_row(factory, sid1).final_recap == ""  # the failure is only logged
    server.recap.script.append(text("You landed on the Reed Shore."))
    sid2 = start(server, cid, narration="Previously, you landed on the shore. What now?")
    assert session_row(factory, sid1).final_recap == "You landed on the Reed Shore."
    resume = str(server.turn.requests[-1]["messages"][-1]["content"])
    assert "You landed on the Reed Shore." in resume and "Resume the Campaign" in resume
    log = server.http.get(f"/log?session={sid2}").json()
    assert [(t["seq"], t["narration"]) for t in log] == [(1, "Previously, you landed on the shore. What now?")]


def test_a_failed_final_recap_never_blocks_the_next_session(factory, server):
    cid = create(server)
    start(server, cid)
    server.recap.script.extend([ClaudeError("down"), ClaudeError("still down")])
    server.http.post("/session/end")
    start(server, cid, narration="Previously...")
    assert server.events[-1] == ("turn_done", {"turn_seq": 1})


def test_session_start_closes_another_campaigns_open_session(factory, server):
    first = create(server)
    second = create(server)
    sid1 = start(server, first)
    server.recap.script.append(text("Fog and reeds."))
    sid2 = start(server, second)
    assert session_row(factory, sid1).ended_at is not None
    assert session_row(factory, sid1).final_recap == "Fog and reeds."
    assert session_row(factory, sid2).ended_at is None
    assert server.http.get("/state").json()["campaign_id"] == second
    assert len(list(server.backups.glob("*.sqlite"))) == 1


def test_the_10th_committed_turn_of_a_session_queues_a_rolling_recap(factory, server):
    sid = start(server, create(server))  # committed Turn 1 of the Session (the opening)
    for i in range(8):
        act(server, f"I wait {i}")
    assert server.recap.requests == []
    server.recap.script.append(text("Ten quiet Turns on the shore."))
    act(server, "I wait once more")  # the 10th
    assert len(server.recap.requests) == 1
    assert session_row(factory, sid).rolling_recap == "Ten quiet Turns on the shore."
    act(server, "I listen")
    assert "Ten quiet Turns on the shore." in str(server.turn.requests[-1]["messages"][-1]["content"])


def test_a_failed_rolling_recap_keeps_the_old_text(factory, server):
    sid = start(server, create(server))
    for i in range(9):
        if i == 8:
            server.recap.script.append(ClaudeError("down"))
        act(server, f"I wait {i}")
    assert session_row(factory, sid).rolling_recap == ""
    assert server.events[-1] == ("turn_done", {"turn_seq": 9})
    # The next rewrite, after the 20th Turn, still covers the Turns the failed one missed.
    for i in range(9, 19):
        if i == 18:
            server.recap.script.append(text("Twenty quiet Turns."))
        act(server, f"I wait {i}")
    retry = server.recap.requests[-1]["messages"][0]["content"]
    assert "Fog on the Reed Shore" in retry and "I wait 0" in retry and "I wait 18" in retry
    assert session_row(factory, sid).rolling_recap == "Twenty quiet Turns."
    # The Final recap covers only the Turns after that rewrite.
    act(server, "I wait 19")
    server.recap.script.append(text("Twenty-one Turns."))
    server.http.post("/session/end")
    final = server.recap.requests[-1]["messages"][0]["content"]
    assert "I wait 19" in final and "I wait 18" not in final and "Twenty quiet Turns." in final


# --- Endings ------------------------------------------------------------------------------------

def test_retire_ends_the_campaign_and_closes_the_session(factory, server):
    cid = create(server)
    sid = start(server, cid)
    server.recap.script.append(text("You gave up the hunt."))
    server.events.clear()
    r = server.http.post(f"/campaigns/{cid}/retire")
    assert r.status_code == 200
    assert server.events == [("state_changed", {"turn_seq": None}),
                             ("campaign_ended", {"campaign_id": cid, "ending": "retired"})]
    assert (campaigns(server)[cid]["status"], campaigns(server)[cid]["ending"]) == ("complete", "retired")
    assert server.http.get("/state").status_code == 404
    assert session_row(factory, sid).final_recap == "You gave up the hunt."
    assert len(server.turn.requests) == 1  # only the opening; retiring makes no Turn call
    assert server.http.post(f"/campaigns/{cid}/retire").status_code == 409


def test_state_lists_only_visible_clocks_as_they_tick(server):
    b = fixture_bible()
    b["clocks"][1]["visible"] = True
    server.plan.script.append(bible_call(b))
    start(server, server.http.post("/campaigns", json=SETUP).json()["campaign_id"])
    assert server.http.get("/state").json()["clocks"] == [
        {"name": "The cult grows suspicious", "filled": 0, "segments": 4}]
    act(server, "I wait", tool("tick_clock", clock="clock.suspicion", segments=2, reason="seen"),
        tool("tick_clock", clock="clock.tide", segments=1, reason="time"), text("Eyes in the fog."))
    assert server.http.get("/state").json()["clocks"] == [
        {"name": "The cult grows suspicious", "filled": 2, "segments": 4}]


def test_an_ending_sends_campaign_ended_and_closes_the_session(factory, server):
    cid = create(server)
    sid = start(server, cid)
    server.recap.script.append(text("The tide took the village."))
    server.events.clear()
    act(server, "I sleep", tool("tick_clock", clock="clock.tide", segments=3, reason="delay"), text("Waves."))
    act(server, "I sleep on", tool("tick_clock", clock="clock.tide", segments=3, reason="delay"),
        tool("end_campaign", ending="defeat"), text("The bell drowns the village."))
    assert server.events[-1] == ("campaign_ended", {"campaign_id": cid, "ending": "defeat"})
    assert server.events.kinds()[-3:] == ["state_changed", "turn_done", "campaign_ended"]
    assert server.http.get("/state").status_code == 404
    assert session_row(factory, sid).final_recap == "The tide took the village."
    assert len(list(server.backups.glob("*.sqlite"))) == 1


# --- Equip --------------------------------------------------------------------------------------

def item_id(state, ref):
    return next(i["id"] for i in state["character"]["inventory"] if i["item"] == ref)


def test_unequip_and_equip_change_armor_class_without_a_claude_call(server):
    start(server, create(server))  # Wren the rogue: leather 11 + Dex 3 = AC 14
    leather = item_id(server.http.get("/state").json(), "leather")
    server.events.clear()
    r = server.http.post(f"/inventory/{leather}/unequip")
    assert r.status_code == 200 and r.json()["character"]["ac"] == 13  # unarmored 10 + Dex 3
    assert server.events == [("state_changed", {"turn_seq": None})]
    assert server.http.post(f"/inventory/{leather}/equip").json()["character"]["ac"] == 14
    assert len(server.turn.requests) == 1
    rations = item_id(server.http.get("/state").json(), "rations")
    assert server.http.post(f"/inventory/{rations}/equip").status_code == 400
    assert server.http.post("/inventory/9999/equip").status_code == 404


def test_equipping_armor_takes_off_the_armor_worn(server):
    start(server, create(server, template="fighter"))  # Bram: chain mail 16 + Defense 1 + shield 2 = AC 19
    act(server, "I take the leather jerkin", tool("add_item", item="leather"), text("It fits."))
    state = server.http.get("/state").json()
    state = server.http.post(f"/inventory/{item_id(state, 'leather')}/equip").json()
    worn = {i["item"] for i in state["character"]["inventory"] if i["equipped"]}
    assert worn == {"leather", "shield", "longsword"}  # R17
    assert state["character"]["ac"] == 16  # leather 11 + Dex 2 + Defense 1 + shield 2


def test_equip_is_refused_during_an_encounter(server):
    start(server, create(server))
    act(server, "I draw on the goblin", tool("start_encounter", monsters=[{"monster": "goblin"}]), text("A goblin!"))
    state = server.http.get("/state").json()
    assert "Goblin 1" in [c["name"] for c in state["encounter"]["order"]]
    assert server.http.post(f"/inventory/{item_id(state, 'leather')}/unequip").status_code == 409


# --- Encounter panel ----------------------------------------------------------------------------

def fight(s, count=3):
    start(s, create(s))
    act(s, "I draw on the goblins", tool("start_encounter", monsters=[{"monster": "goblin", "count": count}]),
        text("Goblins!"))


def test_state_has_no_encounter_without_a_fight(server):
    start(server, create(server))
    assert server.http.get("/state").json()["encounter"] is None


def test_state_returns_the_encounter_in_initiative_order_without_hp_or_ac(server):
    fight(server)
    enc = server.http.get("/state").json()["encounter"]
    names = [c["name"] for c in enc["order"]]
    assert sorted(names) == ["Goblin 1", "Goblin 2", "Goblin 3", "Wren"]
    inits = [c["initiative"] for c in enc["order"]]
    assert inits == sorted(inits, reverse=True)
    assert enc["round"] == 1 and enc["active"] in names
    assert all(set(c) == {"name", "initiative", "conditions", "health"} for c in enc["order"])
    assert set(enc) == {"round", "active", "order"}


def test_each_health_word_is_returned_at_its_boundary(factory, server):
    fight(server, count=4)
    with factory() as db:
        gobs = {c.name: c for c in db.scalars(select(Combatant))}
        for name, hp, status in [("Goblin 1", 5, "active"), ("Goblin 2", 4, "active"),  # just above, exactly half
                                 ("Goblin 3", 0, "dead"), ("Goblin 4", 0, "knocked_out")]:
            gobs[name].hp, gobs[name].hp_max, gobs[name].status = hp, 8, status
        db.commit()
    health = {c["name"]: c["health"] for c in server.http.get("/state").json()["encounter"]["order"]}
    assert health == {"Wren": "unhurt", "Goblin 1": "wounded", "Goblin 2": "bloodied", "Goblin 3": "down",
                      "Goblin 4": "down"}


def test_the_encounter_is_null_once_it_ends(server):
    fight(server)
    act(server, "They flee", tool("end_encounter"), text("Gone."))
    assert server.http.get("/state").json()["encounter"] is None


# --- SSE over the wire --------------------------------------------------------------------------

def test_events_reach_an_sse_stream_over_the_wire(factory, tmp_path):
    turn = FakeClaude()
    app = create_app(factory, turn_client=turn, plan_client=FakeClaude(bible_call()), recap_client=FakeClaude(),
                     backup_dir=tmp_path / "backups", inline=True)
    srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning"))
    thread = threading.Thread(target=srv.run, daemon=True)
    thread.start()
    while not srv.started:
        time.sleep(0.01)
    port = srv.servers[0].sockets[0].getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    try:
        cid = httpx.post(f"{base}/campaigns", json=SETUP).json()["campaign_id"]
        with httpx.stream("GET", f"{base}/events", timeout=5) as stream:
            lines = stream.iter_lines()
            assert [next(lines), next(lines)] == [": connected", ""]  # sent once subscribed
            turn.script.append(text("Fog."))
            httpx.post(f"{base}/session/start", json={"campaign_id": cid}, timeout=5)
            got = []
            for line in lines:
                got.append(line)
                if line.startswith("event: turn_done"):
                    break
        assert got[:3] == ["event: narration_delta", 'data: {"turn_seq": 0, "text": "Fog."}', ""]
        assert "event: state_changed" in got
    finally:
        srv.should_exit = True
        thread.join(5)


# --- web bundle ---------------------------------------------------------------------------------

def test_the_web_bundle_is_served_at_root_without_shadowing_the_api(make_server, tmp_path):
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "index.html").write_text("<!doctype html><title>Pi Dungeon Master</title>")
    http = make_server(web_dir=tmp_path / "web").http
    r = http.get("/")
    assert r.status_code == 200 and "<title>Pi Dungeon Master</title>" in r.text
    assert http.get("/health").json() == {"status": "ok"}
    assert http.get("/campaigns").json() == []


def test_the_dev_server_proxies_every_api_path(server):
    config = (Path(__file__).parents[1] / "src" / "web" / "vite.config.ts").read_text(encoding="utf-8")
    proxied = set(re.findall(r'"(/[a-z]+)"', re.search(r"const api = \[(.*?)\]", config).group(1)))
    served = {"/" + r.path.split("/")[1] for r in server.http.app.routes if isinstance(r, APIRoute)}
    assert served == proxied


def test_root_is_absent_when_the_web_bundle_folder_is_missing(make_server, tmp_path):
    http = make_server(web_dir=tmp_path / "missing").http
    assert http.get("/").status_code == 404
    assert http.get("/health").json() == {"status": "ok"}


def test_the_dev_clients_play_a_campaign_with_rolls_and_a_failed_turn(factory, tmp_path, monkeypatch):
    monkeypatch.setenv("PIDM_FAKE_DELAY", "0")
    app = create_app(factory, turn_client=DevClaude("turn"), plan_client=DevClaude("plan"),
                     recap_client=DevClaude("recap"), backup_dir=tmp_path / "backups", inline=True)
    events = Events()
    app.state.broadcaster.subscribe(events)
    http = TestClient(app)
    cid = http.post("/campaigns", json=SETUP).json()["campaign_id"]
    sid = http.post("/session/start", json={"campaign_id": cid}).json()["session_id"]
    events.clear()
    http.post("/action", json={"text": "I roll to search"})
    assert events.kinds() == ["roll", "narration_delta", "state_changed", "turn_done"]
    events.clear()
    http.post("/action", json={"text": "I fail on purpose"})
    assert events.kinds() == ["error"]
    assert [t["player_text"] for t in http.get(f"/log?session={sid}").json()] == ["", "I roll to search"]
    assert http.post("/session/end").status_code == 202


def test_the_dev_clients_start_hurt_and_end_a_fight(factory, tmp_path, monkeypatch):
    monkeypatch.setenv("PIDM_FAKE_DELAY", "0")
    app = create_app(factory, turn_client=DevClaude("turn"), plan_client=DevClaude("plan"),
                     recap_client=DevClaude("recap"), backup_dir=tmp_path / "backups", inline=True)
    http = TestClient(app)
    cid = http.post("/campaigns", json=SETUP).json()["campaign_id"]
    http.post("/session/start", json={"campaign_id": cid})

    def goblin_1():
        return next(c["health"] for c in http.get("/state").json()["encounter"]["order"] if c["name"] == "Goblin 1")

    http.post("/action", json={"text": "I fight"})
    assert goblin_1() == "unhurt"
    http.post("/action", json={"text": "I hit it"})
    assert goblin_1() == "wounded"
    http.post("/action", json={"text": "I hit it"})
    assert goblin_1() == "bloodied"
    http.post("/action", json={"text": "I hit it"})
    assert goblin_1() == "down"
    http.post("/action", json={"text": "They flee"})
    assert http.get("/state").json()["encounter"] is None


def test_the_dev_plan_client_gives_each_regeneration_a_new_premise(factory, tmp_path, monkeypatch):
    monkeypatch.setenv("PIDM_FAKE_DELAY", "0")
    app = create_app(factory, turn_client=DevClaude("turn"), plan_client=DevClaude("plan"),
                     recap_client=DevClaude("recap"), backup_dir=tmp_path / "backups", inline=True)
    http = TestClient(app)
    cid = http.post("/campaigns", json=SETUP).json()["campaign_id"]
    first = http.get("/campaigns").json()[0]["premise"]
    http.post(f"/campaigns/{cid}/regenerate")
    second = http.get("/campaigns").json()[0]["premise"]
    assert first == fixture_bible()["premise"]
    assert second == f"{first} (take 2)"


# --- Roll prompts, the sheet, Player notes and Auto-roll (issue #26) -----------------------------------

def manual_rolls(factory):
    from conftest import set_auto_roll
    set_auto_roll(factory, False)


def post_in_thread(server, path, **body):
    box = {}
    t = threading.Thread(target=lambda: box.update(r=server.http.post(path, json=body)))
    t.start()
    return t, box


def wait_for_event(server, kind):
    end = time.time() + 5
    while kind not in server.events.kinds():
        assert time.time() < end, server.events.kinds()
        time.sleep(0.01)


def test_a_roll_prompt_holds_the_turn_until_the_roll_endpoint_answers_it(server, factory):
    start(server, create(server))
    manual_rolls(factory)
    server.events.clear()
    assert server.http.post("/roll", json={"turn_seq": 1, "n": 0}).status_code == 409  # nothing to answer
    server.turn.script.extend([tool("skill_check", skill="perception", dc=12), text("A tripwire.")])
    t, box = post_in_thread(server, "/action", text="I look")
    wait_for_event(server, "roll_prompt")
    state = server.http.get("/state").json()
    prompt = state["pending_prompt"]
    assert state["running_turn_seq"] == 1 and prompt["turn_seq"] == 1
    assert (prompt["purpose"], prompt["bonus"], prompt["target"]) == ("Wren perception check", 3, 12)
    assert server.http.post("/roll", json={"turn_seq": 1, "n": 1}).status_code == 409  # not the open prompt
    assert server.http.post("/roll", json={"turn_seq": 1, "n": 0}).status_code == 200
    t.join(5)
    assert box["r"].status_code == 202
    assert server.events.kinds() == ["roll_prompt", "roll", "narration_delta", "state_changed", "turn_done"]
    state = server.http.get("/state").json()
    assert state["pending_prompt"] is None and state["running_turn_seq"] is None


def test_auto_roll_is_off_by_default_persists_and_answers_an_open_prompt(server, factory):
    cid = create(server)
    start(server, cid)
    manual_rolls(factory)
    assert server.http.get("/state").json()["auto_roll"] is False
    server.turn.script.extend([tool("skill_check", skill="perception", dc=12), text("A tripwire.")])
    t, _ = post_in_thread(server, "/action", text="I look")
    wait_for_event(server, "roll_prompt")
    assert server.http.put(f"/campaigns/{cid}/auto_roll", json={"on": True}).json() == {"auto_roll": True}
    t.join(5)  # turning it on rolled for the player
    assert "roll" in server.events.kinds() and server.http.get("/state").json()["auto_roll"] is True
    assert server.http.put("/campaigns/999/auto_roll", json={"on": True}).status_code == 404


def test_the_state_carries_the_sheet_fields_for_the_skills_tab(server):
    start(server, create(server))  # Pip: Rogue 1, Dex 17, Wis 13, Expertise in Stealth, lightfoot halfling
    ch = server.http.get("/state").json()["character"]
    assert ch["speed"] == 25 and ch["proficiency_bonus"] == 2 and ch["ac"] == 14
    assert ch["abilities"]["dex"] == {"score": 17, "mod": 3} and ch["saves"]["dex"] == 5
    skills = {s["skill"]: s for s in ch["skill_list"]}
    assert len(skills) == 18
    assert skills["stealth"] == {"skill": "stealth", "ability": "dex", "bonus": 7, "proficient": True}  # 3 + 2 * 2
    assert skills["athletics"]["bonus"] == -1 and skills["athletics"]["proficient"] is False
    assert ch["features"]["sneak_attack"] == "1d6"


def test_player_notes_are_per_campaign_survive_a_failed_turn_and_never_reach_claude(server):
    a = create(server)
    b = create(server)
    start(server, a)
    assert server.http.get(f"/campaigns/{a}/notes").json() == {"text": ""}
    assert server.http.put(f"/campaigns/{a}/notes", json={"text": "The ferryman lies."}).status_code == 200
    server.http.put(f"/campaigns/{b}/notes", json={"text": "Other story."})
    server.turn.script.append(ClaudeError("overloaded"))
    server.http.post("/action", json={"text": "I wait"})
    assert server.events.kinds()[-1] == "error"
    assert server.http.get(f"/campaigns/{a}/notes").json() == {"text": "The ferryman lies."}
    assert server.http.get(f"/campaigns/{b}/notes").json() == {"text": "Other story."}
    act(server, "I look around")
    for request in server.turn.requests:
        assert "ferryman lies" not in str(request) and "Other story" not in str(request)
    assert server.http.get("/campaigns/999/notes").status_code == 404
    assert server.http.put("/campaigns/999/notes", json={"text": "x"}).status_code == 404
