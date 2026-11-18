"""HTTP server: the v1 API and the SSE event stream (design document: API surface, Turn lifecycle).

`create_app` builds the app from injected parts (Seam 4); `from_env` builds it with real Claude clients for
uvicorn (`uvicorn pidm.app:from_env --factory`). Turns, opening Turns and resume Turns run on the turn thread;
bible generation, Recaps and backups run in order on the job thread (ADR 0001). With `inline`, both run on
the request thread before the response returns.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from pidm import srd
from pidm.campaign import Setup, build_campaign, clear_story, new_campaign, retire
from pidm.claude import AnthropicClient, ClaudeClient, plan_client as make_plan_client, recap_client as make_recap_client
from pidm.db import open_db
from pidm.engine import load_state
from pidm.models import Campaign, Session, Turn
from pidm.orchestrator import TurnOrchestrator, next_seq
from pidm.recap import ROLLING_EVERY, write_final_recap, write_rolling_recap
from pidm.templates import TEMPLATES
from pidm.tools import snapshot

log = logging.getLogger("pidm.server")

Emit = Callable[[str, dict], None]


class Broadcaster:
    """Hands every event to every subscriber; events have no ids and are never buffered or replayed."""

    def __init__(self):
        self._subs: list[Emit] = []
        self._lock = threading.Lock()

    def subscribe(self, fn: Emit) -> None:
        with self._lock:
            self._subs.append(fn)

    def unsubscribe(self, fn: Emit) -> None:
        with self._lock:
            self._subs.remove(fn)

    def __call__(self, event: str, payload: dict) -> None:
        with self._lock:
            subs = list(self._subs)
        for fn in subs:
            fn(event, payload)


class Worker:
    """One thread running submitted work in order, or the caller's thread when inline."""

    def __init__(self, name: str, inline: bool):
        self.pool = None if inline else ThreadPoolExecutor(1, thread_name_prefix=name)

    def submit(self, fn: Callable, *args) -> Future:
        def logged():
            try:
                return fn(*args)
            except Exception:
                log.exception("%s failed", getattr(fn, "__name__", fn))
                raise

        if self.pool:
            return self.pool.submit(logged)
        fut: Future = Future()
        try:
            fut.set_result(logged())
        except Exception as e:
            fut.set_exception(e)
        return fut


class CampaignIn(BaseModel):
    setting: str = Field(min_length=1)
    tone: str = Field(min_length=1)
    length: Literal["one-shot", "short"]
    template: Literal[tuple(TEMPLATES)]  # type: ignore[valid-type]
    character_name: str = ""
    hook: str = ""
    lines: str = ""
    veils: str = ""


class ActionIn(BaseModel):
    text: str = Field(min_length=1)


class SessionStartIn(BaseModel):
    campaign_id: int


def _open_session(db) -> Session | None:
    return db.scalar(select(Session).where(Session.ended_at.is_(None)))


def _conflict(message: str) -> HTTPException:
    return HTTPException(409, message)


def create_app(factory: sessionmaker, *, turn_client: ClaudeClient, plan_client: ClaudeClient,
               recap_client: ClaudeClient, backup_dir: str | Path, inline: bool = False, round_cap: int = 4,
               context_budget: int = 8000, web_dir: str | Path | None = None) -> FastAPI:
    app = FastAPI(title="Pi Dungeon Master")
    emit = app.state.broadcaster = Broadcaster()
    orch = TurnOrchestrator(factory, turn_client, round_cap=round_cap, context_budget=context_budget)
    turns, jobs = Worker("turn", inline), Worker("job", inline)
    backup_dir = Path(backup_dir)
    # Held from an accepted request until its Turn ends, so a second action, a Session change or a direct
    # action is refused with 409 instead of queueing behind it.
    busy = threading.Lock()
    running: dict[str, int | None] = {"seq": None}

    with factory() as db:  # a Campaign still generating lost its job when the server stopped
        for camp in db.scalars(select(Campaign).where(Campaign.status == "generating")):
            camp.status, camp.setup_error = "failed", "The server restarted while the bible was being generated."
        db.commit()

    # --- shared paths ---------------------------------------------------------------------

    def claim() -> None:
        if not busy.acquire(blocking=False):
            raise _conflict("A Turn is running.")

    def backup(session_id: int) -> None:
        backup_dir.mkdir(parents=True, exist_ok=True)
        path = backup_dir / f"pidm-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-session{session_id}.sqlite"
        try:
            with factory.kw["bind"].connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                conn.exec_driver_sql("VACUUM INTO ?", (str(path),))
        except Exception:
            log.exception("Backup after Session %s failed", session_id)

    def close_job(session_id: int) -> None:
        write_final_recap(factory, recap_client, session_id)
        backup(session_id)

    def close_session(db, sess: Session) -> None:
        """End a Session now; the job thread writes its Final recap and then a backup."""
        sess.ended_at = datetime.now(timezone.utc)
        db.commit()
        jobs.submit(close_job, sess.id)

    def after_turn(session_id: int, turn: Turn) -> None:
        if turn.status != "committed":
            return
        with factory() as db:
            count = db.scalar(select(func.count()).select_from(Turn)
                              .where(Turn.session_id == session_id, Turn.status == "committed"))
            if count % ROLLING_EVERY == 0:
                jobs.submit(write_rolling_recap, factory, recap_client, session_id, count)
            sess = db.get(Session, session_id)
            if sess.campaign.status == "complete" and sess.ended_at is None:
                close_session(db, sess)  # an Ending closes the Session

    def run(session_id: int, work: Callable[[], Turn]) -> None:
        try:
            after_turn(session_id, work())
        finally:
            running["seq"] = None
            busy.release()

    def start_turn(session_id: int, seq: int, work: Callable[[], Turn]) -> None:
        running["seq"] = seq
        try:
            turns.submit(run, session_id, work)
        except BaseException:
            running["seq"] = None
            busy.release()
            raise

    def state_json(db, sess: Session) -> dict:
        state = load_state(db, sess.id, None)
        snap = snapshot(state)
        snap["character"]["inventory"] = [{"id": i.id, "item": i.item_ref, "qty": i.qty, "equipped": i.equipped}
                                          for i in state.character.inventory]
        return {"session_id": sess.id, "campaign_id": sess.campaign_id, "campaign_name": sess.campaign.name,
                "running_turn_seq": running["seq"], "encounter": None, **snap,
                "clocks": [{"name": c.name, "filled": c.filled, "segments": c.segments}
                           for c in sess.campaign.clocks if c.visible]}

    # --- endpoints -------------------------------------------------------------------------

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/campaigns", status_code=202)
    def create_campaign(body: CampaignIn) -> dict:
        setup = Setup(setting=body.setting, tone=body.tone, length=body.length, lines=body.lines, veils=body.veils,
                      hook=body.hook)
        with factory() as db:
            camp = new_campaign(setup, body.template, body.character_name, "generating")
            db.add(camp)
            db.commit()
            cid = camp.id
        jobs.submit(build_campaign, factory, plan_client, cid)
        return {"campaign_id": cid}

    @app.get("/campaigns")
    def list_campaigns() -> list[dict]:
        with factory() as db:
            return [{"id": c.id, "name": c.name, "status": c.status, "length": c.length,
                     "premise": c.premise if c.status in ("ready", "active", "complete") else None,
                     "ending": c.ending, "setup_error": c.setup_error}
                    for c in db.scalars(select(Campaign).order_by(Campaign.id))]

    @app.post("/campaigns/{campaign_id}/regenerate", status_code=202)
    def regenerate(campaign_id: int) -> dict:
        with factory() as db:
            camp = db.get(Campaign, campaign_id)
            if camp is None:
                raise HTTPException(404, "No such Campaign.")
            if camp.status != "ready":
                raise _conflict(f"Only a ready Campaign can be regenerated; this one is {camp.status}.")
            clear_story(camp)
            camp.status = "generating"
            db.commit()
        jobs.submit(build_campaign, factory, plan_client, campaign_id)
        return {"campaign_id": campaign_id}

    @app.post("/campaigns/{campaign_id}/retire")
    def retire_campaign(campaign_id: int) -> dict:
        claim()
        try:
            with factory() as db:
                camp = db.get(Campaign, campaign_id)
                if camp is None:
                    raise HTTPException(404, "No such Campaign.")
                if camp.status not in ("ready", "active"):
                    raise _conflict(f"The Campaign is {camp.status}.")
            retire(factory, campaign_id)
            emit("state_changed", {"turn_seq": None})
            emit("campaign_ended", {"campaign_id": campaign_id, "ending": "retired"})
            with factory() as db:
                sess = _open_session(db)
                if sess is not None and sess.campaign_id == campaign_id:
                    close_session(db, sess)
            return {"campaign_id": campaign_id, "ending": "retired"}
        finally:
            busy.release()

    @app.get("/state")
    def get_state() -> dict:
        with factory() as db:
            sess = _open_session(db)
            if sess is None:
                raise HTTPException(404, "No Session is open.")
            return state_json(db, sess)

    @app.get("/log")
    def get_log(session: int) -> list[dict]:
        with factory() as db:
            rows = db.scalars(select(Turn).where(Turn.session_id == session, Turn.status == "committed")
                              .order_by(Turn.seq)).all()
            return [{"seq": t.seq, "player_text": t.player_text, "narration": t.narration,
                     "rolls": [{"purpose": r.purpose, "expr": r.expr, "dice": r.dice, "total": r.total,
                                "target": r.target, "outcome": r.outcome} for r in t.rolls]} for t in rows]

    @app.post("/action", status_code=202)
    def action(body: ActionIn) -> dict:
        claim()
        try:
            with factory() as db:
                sess = _open_session(db)
                if sess is None:
                    raise _conflict("No Session is open.")
                sid, seq = sess.id, next_seq(db, sess.campaign_id)
        except BaseException:
            busy.release()
            raise
        start_turn(sid, seq, lambda: orch.run_turn(sid, body.text, emit))
        return {"turn_seq": seq}

    @app.post("/session/start", status_code=202)
    def session_start(body: SessionStartIn) -> dict:
        claim()
        try:
            with factory() as db:
                camp = db.get(Campaign, body.campaign_id)
                if camp is None:
                    raise HTTPException(404, "No such Campaign.")
                if camp.status not in ("ready", "active"):
                    raise _conflict(f"The Campaign is {camp.status}.")
                for other in db.scalars(select(Session).where(Session.ended_at.is_(None))).all():
                    close_session(db, other)
                camp.status = "active"  # accepting a ready premise
                sess = Session(campaign=camp)
                db.add(sess)
                db.commit()
                sid, cid, seq = sess.id, camp.id, next_seq(db, camp.id)
                resume = db.scalar(select(func.count()).select_from(Turn).join(Session).where(
                    Session.campaign_id == cid, Turn.status == "committed")) > 0
        except BaseException:
            busy.release()
            raise

        def open_session() -> Turn:
            # Queued behind any close job, so a just-closed Session's Final recap is written once.
            jobs.submit(missing_final_recaps, cid, sid).result()
            return (orch.run_resume if resume else orch.run_opening)(sid, emit)

        start_turn(sid, seq, open_session)
        return {"session_id": sid}

    def missing_final_recaps(campaign_id: int, current: int) -> None:
        with factory() as db:
            ids = db.scalars(select(Session.id).where(Session.campaign_id == campaign_id, Session.id != current,
                                                      Session.final_recap == "")).all()
        for session_id in ids:
            write_final_recap(factory, recap_client, session_id)  # a failure falls back to the Rolling recap

    @app.post("/session/end", status_code=202)
    def session_end() -> dict:
        claim()
        try:
            with factory() as db:
                sess = _open_session(db)
                if sess is None:
                    raise _conflict("No Session is open.")
                close_session(db, sess)
                return {"session_id": sess.id}
        finally:
            busy.release()

    def set_equipped(item_id: int, on: bool) -> dict:
        claim()
        try:
            with factory() as db:
                sess = _open_session(db)
                if sess is None:
                    raise HTTPException(404, "No Session is open.")
                state = load_state(db, sess.id, None)
                if state.encounter is not None:
                    raise _conflict("Gear can't change during an Encounter.")  # R17
                inv = state.character.inventory
                item = next((i for i in inv if i.id == item_id), None)
                if item is None:
                    raise HTTPException(404, "The Character has no such item.")
                ref = item.item_ref
                if on:
                    if ref not in srd.WEAPONS and ref not in srd.ARMOR and ref != srd.SHIELD:
                        raise HTTPException(400, f"{ref} is not armor, a shield or a weapon.")  # R17
                    if ref in srd.ARMOR:
                        for other in inv:
                            if other.item_ref in srd.ARMOR:
                                other.equipped = False  # one suit of armor at a time (R17)
                item.equipped = on
                db.commit()
                out = state_json(db, sess)
            emit("state_changed", {"turn_seq": None})
            return out
        finally:
            busy.release()

    @app.post("/inventory/{item_id}/equip")
    def equip(item_id: int) -> dict:
        return set_equipped(item_id, True)

    @app.post("/inventory/{item_id}/unequip")
    def unequip(item_id: int) -> dict:
        return set_equipped(item_id, False)

    @app.get("/events")
    async def events(request: Request) -> StreamingResponse:
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def push(event: str, payload: dict) -> None:
            try:
                loop.call_soon_threadsafe(queue.put_nowait, (event, payload))
            except RuntimeError:
                pass  # the loop has closed

        emit.subscribe(push)

        async def stream():
            try:
                yield ": connected\n\n"
                while True:
                    try:
                        event, payload = await asyncio.wait_for(queue.get(), 15)
                    except asyncio.TimeoutError:
                        if await request.is_disconnected():
                            break
                        yield ": ping\n\n"  # keeps proxies from closing an idle stream
                        continue
                    yield f"event: {event}\ndata: {json.dumps(payload)}\n\n"
            finally:
                emit.unsubscribe(push)

        return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})

    # Mounted last so every API route above wins; without a built bundle the API runs alone.
    if web_dir is not None and Path(web_dir).is_dir():
        app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")

    return app


def from_env() -> FastAPI:
    """The real app: SQLite at PIDM_DB, backups in PIDM_BACKUP_DIR, the web bundle from PIDM_WEB_DIR, Claude clients
    from the environment."""
    db_path = os.environ.get("PIDM_DB", "data/pidm.sqlite")
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    return create_app(open_db(db_path), turn_client=AnthropicClient(), plan_client=make_plan_client(),
                      recap_client=make_recap_client(), backup_dir=os.environ.get("PIDM_BACKUP_DIR", "/backups"),
                      round_cap=int(os.environ.get("PIDM_ROUND_CAP", "4")),
                      context_budget=int(os.environ.get("PIDM_CONTEXT_BUDGET", "8000")),
                      web_dir=os.environ.get("PIDM_WEB_DIR", "src/web/dist"))
