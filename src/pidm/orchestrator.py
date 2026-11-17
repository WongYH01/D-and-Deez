"""Turn orchestrator: runs one Turn from player action to committed Narration.

It knows nothing about the terminal or HTTP; it reports through `emit(event, payload)` with the
events roll, narration_delta, turn_done (with the Campaign's ending, if any) and error. M4 wires the same object to SSE.
"""

from __future__ import annotations

import json
import threading
from typing import Callable

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from pidm.claude import ClaudeClient, Reply, Usage
from pidm.dice import Dice
from pidm.engine import load_state
from pidm.models import RollRecord, Session, Turn
from pidm.prompts import OPENING, system_prompt, user_message
from pidm.rules import retrieve
from pidm.story import director_block, end, ending_met
from pidm.tools import dispatch, snapshot, tool_definitions

Emit = Callable[[str, dict], None]


class TurnAlreadyRunning(Exception):
    pass


class CampaignEnded(Exception):
    pass


def strip_prose(content: list[dict]) -> list[dict]:
    """ADR 0003: text written in a Tool round that calls tools is never shown and is removed before the next round.

    Thinking blocks are bound to the message they came in, so a message that loses text also drops them.
    """
    if not any(b["type"] == "text" for b in content):
        return content
    return [b for b in content if b["type"] not in ("text", "thinking", "redacted_thinking")]


def text_of(reply: Reply) -> str:
    return "".join(b["text"] for b in reply.content if b["type"] == "text")


class TurnOrchestrator:
    def __init__(self, factory: sessionmaker, client: ClaudeClient, *, round_cap: int = 4,
                 history_turns: int = 8, rng: Callable[[int], int] | None = None):
        self.factory = factory
        self.client = client
        self.round_cap = round_cap
        self.history_turns = history_turns
        self.rng = rng
        self._lock = threading.Lock()
        self.running = False

    def run_opening(self, session_id: int, emit: Emit) -> Turn:
        """Turn 0: Claude narrates the bible's opening scene."""
        return self.run_turn(session_id, OPENING, emit)

    def run_turn(self, session_id: int, player_text: str, emit: Emit) -> Turn:
        if not self._lock.acquire(blocking=False):
            raise TurnAlreadyRunning("A Turn is already running.")
        self.running = True
        try:
            with self.factory() as db:
                camp = db.get(Session, session_id).campaign
                if camp.status != "active":
                    raise CampaignEnded(f"The Campaign has ended ({camp.ending}).")
            return self._run(session_id, player_text, emit)
        finally:
            self.running = False
            self._lock.release()

    def _history(self, db, session_id: int) -> list[dict]:
        turns = db.scalars(
            select(Turn).where(Turn.session_id == session_id, Turn.status == "committed")
            .order_by(Turn.seq.desc()).limit(self.history_turns)).all()
        messages = []
        for t in reversed(turns):
            messages += [{"role": "user", "content": t.player_text}, {"role": "assistant", "content": t.narration}]
        return messages

    def _run(self, session_id: int, player_text: str, emit: Emit) -> Turn:
        db = self.factory()
        last = db.scalar(select(func.max(Turn.seq)).where(Turn.session_id == session_id))
        seq = 0 if last is None else last + 1
        dice = Dice(rng=self.rng, on_roll=lambda r: emit("roll", {"turn_seq": seq, **r.as_dict()}))
        usage = Usage()
        try:
            state = load_state(db, session_id, dice)
            state.turn = seq
            system = system_prompt(state.campaign)
            tools = tool_definitions()
            context = user_message(snapshot(state), player_text, retrieve(db, player_text), director_block(state))
            messages = self._history(db, session_id) + [{"role": "user", "content": context}]
            narration = None
            for _ in range(self.round_cap):
                reply = self.client.send(system=system, messages=messages, tools=tools, tools_enabled=True, on_text=None)
                usage.add(reply.usage)
                calls = [b for b in reply.content if b["type"] == "tool_use"]
                if not calls:
                    # The final Tool round: only now is its text known to be Narration.
                    narration = text_of(reply)
                    emit("narration_delta", {"turn_seq": seq, "text": narration})
                    break
                messages.append({"role": "assistant", "content": strip_prose(reply.content)})
                results = []
                for call in calls:
                    result = dispatch(state, call["name"], call.get("input") or {})
                    results.append({"type": "tool_result", "tool_use_id": call["id"], "content": json.dumps(result),
                                    **({"is_error": True} if "error" in result else {})})
                messages.append({"role": "user", "content": results})
            if narration is None:
                # Tool round cap reached: one last call with tools disabled, streamed as Narration.
                reply = self.client.send(system=system, messages=messages, tools=tools, tools_enabled=False,
                                         on_text=lambda t: emit("narration_delta", {"turn_seq": seq, "text": t}))
                usage.add(reply.usage)
                narration = text_of(reply)
            if ending_met(state) == "defeat":
                end(state.campaign, "defeat")  # Claude skipped end_campaign on a full Main clock
            turn = Turn(session_id=session_id, seq=seq, player_text=player_text, narration=narration,
                        status="committed", tokens_in=usage.input_tokens, tokens_out=usage.output_tokens,
                        tokens_cached=usage.cached_tokens)
            turn.rolls = [RollRecord(seq=i, purpose=r.purpose[:200], expr=r.expr, dice=r.dice, total=r.total,
                                     target=r.target, outcome=r.outcome) for i, r in enumerate(dice.rolls)]
            db.add(turn)
            db.commit()  # state tree, turn row and rolls in one transaction (ADR 0002)
            emit("turn_done", {"turn_id": turn.id, "turn_seq": seq, "ending": state.campaign.ending})
            return turn
        except Exception as e:
            db.rollback()
            usage.add(getattr(e, "usage", Usage()))
            failed = self._save_failed(session_id, seq, player_text, usage)
            emit("error", {"turn_seq": seq, "message": "The turn failed; nothing changed. Please retype your action.",
                           "detail": str(e), "retryable": True})
            return failed
        finally:
            db.close()

    def _save_failed(self, session_id: int, seq: int, player_text: str, usage: Usage) -> Turn:
        with self.factory() as db:
            turn = Turn(session_id=session_id, seq=seq, player_text=player_text, narration="", status="failed",
                        tokens_in=usage.input_tokens, tokens_out=usage.output_tokens, tokens_cached=usage.cached_tokens)
            db.add(turn)
            db.commit()
            return turn
