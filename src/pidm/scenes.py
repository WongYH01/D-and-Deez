"""Scenes: `end_scene`, the 15-Turn automatic end and the Scene summary job (design: Memory strategy, Scenes).

A Scene row exists only once the Scene is finished. The open Scene starts at the Turn after the Campaign's last
finished Scene (Turn 0 for the first), so a Scene can span Sessions. The row is added to the Turn's state tree and
commits with the Turn; the summary comes later from the job thread.
"""

from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from pidm.claude import ClaudeClient
from pidm.engine import GameState, ToolError
from pidm.models import Scene, Session, Turn

log = logging.getLogger("pidm.scenes")

MAX_SCENE_TURNS = 15  # Memory strategy: a Scene ends after 15 Turns without end_scene
SCENE_WORDS = 120

SCENE_SYSTEM = """You summarise one finished scene of a single-player Dungeons & Dragons game, for the Dungeon \
Master to recall later. Write plain prose in the past tense and second person ("you"), with no headings or lists. \
Keep the place, the people met, what was decided, items gained or lost, and open threads. Never invent events."""


def open_scene_start(state: GameState) -> int:
    """The seq of the open Scene's first Turn."""
    last = state.db.scalar(select(func.max(Scene.end_turn)).join(Session)
                           .where(Session.campaign_id == state.campaign.id))
    return 0 if last is None else last + 1


def end_scene(state: GameState) -> Scene:
    scene = Scene(session_id=state.session.id, start_turn=open_scene_start(state), end_turn=state.turn)
    state.db.add(scene)
    state.db.flush()
    return scene


def t_end_scene(state: GameState, reason: str) -> dict:
    if state.encounter is not None:
        raise ToolError("An Encounter is active; end it first.")
    if open_scene_start(state) > state.turn:
        raise ToolError("The Scene already ended this Turn.")
    end_scene(state)
    return {"ended": True, "reason": reason}


def end_overlong_scene(state: GameState) -> None:
    """Called at commit. shortcut: counts seq numbers, so a failed Turn counts toward the 15; fine for one player."""
    start = open_scene_start(state)
    # An Encounter is never split: the Scene runs on until it ends, as end_scene refuses to cut it too.
    if start <= state.turn and state.turn - start + 1 >= MAX_SCENE_TURNS and state.encounter is None:
        end_scene(state)


def write_scene_summary(factory: sessionmaker, client: ClaudeClient, scene_id: int) -> None:
    """Summarise a finished Scene from its committed Turns; a failed call leaves the summary empty (not recalled)."""
    with factory() as db:
        scene = db.get(Scene, scene_id)
        if scene.summary:
            return
        campaign_id = db.get(Session, scene.session_id).campaign_id
        turns = db.scalars(select(Turn).join(Session).where(
            Session.campaign_id == campaign_id, Turn.status == "committed",
            Turn.seq.between(scene.start_turn, scene.end_turn)).order_by(Turn.seq)).all()
        transcript = "\n\n".join(f"Player: {t.player_text}\nDM: {t.narration}" for t in turns)
    if not transcript:
        return
    msg = f"Scene:\n{transcript}\n\nSummarise the scene in at most {SCENE_WORDS} words. Reply with the summary only."
    try:
        reply = client.send(system=SCENE_SYSTEM, messages=[{"role": "user", "content": msg}], tools=[],
                            tools_enabled=False, on_text=None)
        summary = "".join(b["text"] for b in reply.content if b["type"] == "text").strip()
    except Exception:
        log.exception("Summary of Scene %s failed; the Scene is not recalled", scene_id)
        return
    with factory() as db:
        db.get(Scene, scene_id).summary = summary
        db.commit()
