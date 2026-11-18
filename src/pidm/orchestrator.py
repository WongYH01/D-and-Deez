"""Turn orchestrator: runs one Turn from player action to committed Narration.

It knows nothing about the terminal or HTTP; it reports through `emit(event, payload)` with the
events roll_prompt, roll, narration_delta, narration_discard, state_changed, turn_done, campaign_ended and error.
The server passes its broadcaster.
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
from pidm.memory import HOPS, memory_blocks
from pidm.models import Campaign, RollRecord, Session, Turn
from pidm.prompts import OPENING, RESUME, system_prompt, user_message
from pidm.recap import recap_block
from pidm.scenes import end_overlong_scene
from pidm.sources import location_text
from pidm.recall import Embedder, recall
from pidm.rules import retrieve
from pidm.story import director_block, end, ending_met
from pidm.tools import dispatch, snapshot, tool_definitions

Emit = Callable[[str, dict], None]
CACHE = {"type": "ephemeral"}  # the default 5-minute lifetime


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


def next_seq(db, campaign_id: int) -> int:
    """Turns are numbered across the Campaign: 0 is its opening, and failed Turns use up a number too."""
    last = db.scalar(select(func.max(Turn.seq)).join(Session).where(Session.campaign_id == campaign_id))
    return 0 if last is None else last + 1


def _tokens(chars: int) -> int:
    # shortcut: characters / 4 estimates tokens; switch to the token-counting API if logged counts are far off.
    return chars // 4


def _size(history: list[dict], context: str) -> int:
    return len(context) + sum(len(m["content"]) for m in history)


def trim_history(history: list[dict], context: str, budget: int) -> list[dict]:
    """Drop the oldest action and Narration pairs until the history plus the dynamic context fits the budget.

    The context (state snapshot, Director block, recap block, Rule sections) is never cut; `retrieve` already
    caps Rule sections at two and `_run` has already dropped recall and far Facts, so the oldest pairs are last.
    """
    size = _size(history, context)
    while history and _tokens(size) > budget:
        size -= len(history[0]["content"]) + len(history[1]["content"])
        history = history[2:]
    return history


class TurnOrchestrator:
    def __init__(self, factory: sessionmaker, client: ClaudeClient, *, round_cap: int = 4,
                 history_turns: int = 8, context_budget: int = 8000, rng: Callable[[int], int] | None = None,
                 prompt_timeout: float = 600, embedder: Embedder | None = None):
        self.factory = factory
        self.client = client
        self.round_cap = round_cap
        self.history_turns = history_turns
        self.context_budget = context_budget
        self.rng = rng
        self.embedder = embedder  # None: no Scene recall
        self.prompt_timeout = prompt_timeout  # seconds an unanswered Roll prompt waits before it auto-rolls
        self._lock = threading.Lock()
        self._answered = threading.Event()
        self.running = False
        self.campaign_id: int | None = None  # the running Turn's Campaign
        self.pending: dict | None = None  # the open Roll prompt of the running Turn, for the state view

    def answer_roll(self, turn_seq: int | None = None, n: int | None = None, campaign_id: int | None = None) -> bool:
        """The player clicked Roll: let the waiting Turn go on. False when no Roll prompt is open, or when the
        open one is not the one named (a late click must not answer the next prompt)."""
        p = self.pending
        if p is None or (turn_seq, n) not in ((None, None), (p["turn_seq"], p["n"])):
            return False
        if campaign_id is not None and campaign_id != self.campaign_id:
            return False
        self._answered.set()
        return True

    def run_opening(self, session_id: int, emit: Emit) -> Turn:
        """Turn 0: Claude narrates the bible's opening scene."""
        return self.run_turn(session_id, OPENING, emit)

    def run_resume(self, session_id: int, emit: Emit) -> Turn:
        """The first Turn of a later Session: a short "previously" from the recap block."""
        return self.run_turn(session_id, RESUME, emit)

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
            self.pending = None
            self._lock.release()

    def _history(self, db, campaign_id: int) -> list[dict]:
        """The Campaign's last committed Turns, across Session boundaries."""
        turns = db.scalars(
            select(Turn).join(Session).where(Session.campaign_id == campaign_id, Turn.status == "committed")
            .order_by(Turn.seq.desc()).limit(self.history_turns)).all()
        messages = []
        for t in reversed(turns):
            messages += [{"role": "user", "content": t.player_text}, {"role": "assistant", "content": t.narration}]
        return messages

    def _run(self, session_id: int, player_text: str, emit: Emit) -> Turn:
        db = self.factory()
        campaign_id = db.get(Session, session_id).campaign_id
        self.campaign_id = campaign_id
        seq = next_seq(db, campaign_id)
        asked = {"count": 0, "answered": None}

        def on_roll(r) -> None:
            # The first Roll after an answered prompt names it, so the UI closes that prompt on any arrival order.
            emit("roll", {"turn_seq": seq, **r.as_dict(), "answers_prompt": asked["answered"]})
            asked["answered"] = None

        def prompt(info: dict) -> None:
            with self.factory() as short:
                if short.get(Campaign, campaign_id).auto_roll:
                    return
            n, asked["count"] = asked["count"], asked["count"] + 1
            self._answered.clear()
            self.pending = {"turn_seq": seq, "n": n, **info}
            emit("roll_prompt", self.pending)
            self._answered.wait(self.prompt_timeout)  # a timeout auto-rolls
            self.pending = None
            asked["answered"] = n

        dice = Dice(rng=self.rng, on_roll=on_roll, prompt=prompt)
        usage = Usage()
        try:
            state = load_state(db, session_id, dice)
            state.turn = seq
            # Breakpoint 1 covers the tools and system prompt; breakpoint 2 the final user message, so later
            # Tool rounds of this Turn reread the dynamic context from the cache.
            system = [{"type": "text", "text": system_prompt(state.campaign), "cache_control": CACHE}]
            tools = tool_definitions()
            past = self._history(db, campaign_id)
            # The action and the last two Narrations name the Entities whose Facts Claude needs.
            seen = [player_text] + [m["content"] for m in past[-4:] if m["role"] == "assistant"]

            def build(hops: int, scenes: list[str]) -> str:
                world, notes = memory_blocks(state, seen, hops)
                camp = state.campaign
                source = location_text(db, camp.source_id, camp.current_location) if camp.source_id else None
                return user_message(snapshot(state), player_text, retrieve(db, player_text), director_block(state),
                                    recap_block(db, state.session), world, notes, scenes, source)

            scenes = recall(self.factory, self.embedder, campaign_id, player_text)  # inline; never fails the Turn
            context = build(HOPS, scenes)
            if _tokens(_size(past, context)) > self.context_budget:
                # Memory strategy: Scene recall and Facts more than one hop away go before recent Turns do.
                context = build(1, [])
            history = trim_history(past, context, self.context_budget)
            messages = history + [{"role": "user", "content": [{"type": "text", "text": context,
                                                                "cache_control": CACHE}]}]
            narration = None
            for _ in range(self.round_cap):
                streamed = []
                reply = self.client.send(system=system, messages=messages, tools=tools, tools_enabled=True,
                                         on_text=lambda t: (streamed.append(t), emit("narration_delta", {"turn_seq": seq, "text": t})))
                usage.add(reply.usage)
                calls = [b for b in reply.content if b["type"] == "tool_use"]
                if not calls:
                    narration = text_of(reply)  # the final Tool round: its streamed text is the Narration
                    break
                if streamed:
                    emit("narration_discard", {"turn_seq": seq})  # this round called tools, so its text is not Narration
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
            end_overlong_scene(state)
            met = ending_met(state)  # None once Claude called end_campaign, so no double ending
            if met in ("defeat", "fallen_hero"):
                end(state.campaign, met)  # Claude skipped end_campaign; a Victory still needs Claude's epilogue
            turn = Turn(session_id=session_id, seq=seq, player_text=player_text, narration=narration,
                        status="committed", tokens_in=usage.input_tokens, tokens_out=usage.output_tokens,
                        tokens_cached=usage.cached_tokens)
            turn.rolls = [RollRecord(seq=i, purpose=r.purpose[:200], expr=r.expr, dice=r.dice, total=r.total,
                                     target=r.target, outcome=r.outcome) for i, r in enumerate(dice.rolls)]
            db.add(turn)
            db.commit()  # state tree, turn row and rolls in one transaction (ADR 0002)
            emit("state_changed", {"turn_seq": seq})
            emit("turn_done", {"turn_seq": seq})
            if state.campaign.ending:
                emit("campaign_ended", {"campaign_id": campaign_id, "ending": state.campaign.ending})
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
