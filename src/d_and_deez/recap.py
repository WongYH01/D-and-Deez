"""Session Recaps: the recap block every Turn reads, and the Rolling and Final recap jobs.

The jobs run on the job thread. Each reads in one short transaction, calls the recap model outside any
transaction and writes in another. A failed call keeps the old text and is only logged.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession, sessionmaker

from d_and_deez.claude import ClaudeClient
from d_and_deez.models import Session, Turn

log = logging.getLogger("d_and_deez.recap")

ROLLING_EVERY = 10  # committed Turns of a Session between Rolling recap rewrites
ROLLING_WORDS = 400
FINAL_WORDS = 250

RECAP_SYSTEM = """You keep the recap of a single-player Dungeons & Dragons game for its Dungeon Master. \
Write plain prose in the past tense and second person ("you"), with no headings or lists. Keep the names, \
places, promises, open threads, items gained or lost and the Character's condition. Never invent events or \
reveal anything the player did not see."""


def recap_block(db: DbSession, sess: Session) -> str | None:
    """The previous Session's Final recap (its Rolling recap if the Final one is missing) and this Session's
    Rolling recap; None when there is neither."""
    prev = db.scalar(select(Session).where(Session.campaign_id == sess.campaign_id, Session.id < sess.id)
                     .order_by(Session.id.desc()).limit(1))
    parts = []
    if prev is not None and (prev.final_recap or prev.rolling_recap):
        parts.append(f"Previous Session: {prev.final_recap or prev.rolling_recap}")
    if sess.rolling_recap:
        parts.append(f"This Session so far: {sess.rolling_recap}")
    return "\n\n".join(parts) or None


def committed_turns(db: DbSession, session_id: int) -> list[tuple[str, str]]:
    turns = db.scalars(select(Turn).where(Turn.session_id == session_id, Turn.status == "committed")
                       .order_by(Turn.seq)).all()
    return [(t.player_text, t.narration) for t in turns]


def _summarise(client: ClaudeClient, old: str, turns: list[tuple[str, str]], words: int) -> str:
    transcript = "\n\n".join(f"Player: {a}\nDM: {n}" for a, n in turns) or "(none)"
    msg = (f"Recap so far:\n{old or '(none)'}\n\nTurns since:\n{transcript}\n\n"
           f"Rewrite the recap so it covers all of the above in at most {words} words. Reply with the recap only.")
    reply = client.send(system=RECAP_SYSTEM, messages=[{"role": "user", "content": msg}], tools=[],
                        tools_enabled=False, on_text=None)
    return "".join(b["text"] for b in reply.content if b["type"] == "text").strip()


def write_rolling_recap(factory: sessionmaker, client: ClaudeClient, session_id: int, through: int) -> None:
    """Rewrite the Rolling recap from the old one plus the Session's committed Turns since its last update, up to
    the `through`-th; a failed update leaves those Turns for the next one."""
    with factory() as db:
        sess = db.get(Session, session_id)
        old = sess.rolling_recap
        turns = committed_turns(db, session_id)[sess.rolling_through:through]
    try:
        new = _summarise(client, old, turns, ROLLING_WORDS)
    except Exception:
        log.exception("Rolling recap of Session %s failed; keeping the old text", session_id)
        return
    with factory() as db:
        sess = db.get(Session, session_id)
        sess.rolling_recap, sess.rolling_through = new, through
        db.commit()


def write_final_recap(factory: sessionmaker, client: ClaudeClient, session_id: int) -> None:
    """Write the Final recap of an ended Session that lacks one, from its Rolling recap plus the later Turns."""
    with factory() as db:
        sess = db.get(Session, session_id)
        if sess.final_recap:
            return
        old = sess.rolling_recap
        rest = committed_turns(db, session_id)[sess.rolling_through:]  # the Turns the Rolling recap misses
    if not old and not rest:
        return  # nothing happened in this Session
    try:
        new = _summarise(client, old, rest, FINAL_WORDS)
    except Exception:
        log.exception("Final recap of Session %s failed; the next Session start retries it", session_id)
        return
    with factory() as db:
        db.get(Session, session_id).final_recap = new
        db.commit()
