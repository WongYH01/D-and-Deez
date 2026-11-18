from __future__ import annotations

import copy
import itertools
import json
import random as _random
from pathlib import Path

import pytest
from sqlalchemy import ColumnDefault, select

from pidm.campaign import Setup, start_campaign
from pidm.claude import Reply, Usage
from pidm.db import open_db
from pidm.dice import Dice
from pidm.engine import load_state
from pidm.models import Campaign, Session
from pidm.templates import create_character
from pidm.tools import dispatch


FIXTURE_BIBLE = Path(__file__).parent / "fixtures" / "one_shot_bible.json"


def fixture_bible() -> dict:
    return json.loads(FIXTURE_BIBLE.read_text(encoding="utf-8"))


_ids = itertools.count(1)


def tool(name, **args):
    return {"type": "tool_use", "id": f"toolu_{next(_ids)}", "name": name, "input": args}


def text(t):
    return {"type": "text", "text": t}


class FakeClaude:
    """Returns scripted replies in order; an Exception in the script is raised instead."""

    def __init__(self, *script):
        self.script = list(script)
        self.requests = []

    def send(self, *, system, messages, tools, tools_enabled, on_text, force_tool=None):
        self.requests.append({"system": system, "messages": copy.deepcopy(messages), "tools_enabled": tools_enabled,
                              "tools": tools, "force_tool": force_tool})
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        blocks = item if isinstance(item, list) else [item]
        if on_text:
            for b in blocks:
                if b["type"] == "text":
                    on_text(b["text"])
        stop = "tool_use" if any(b["type"] == "tool_use" for b in blocks) else "end_turn"
        return Reply(content=blocks, stop_reason=stop, usage=Usage(100, 20, 60))


class Events(list):
    def __call__(self, event, payload):
        self.append((event, payload))

    def kinds(self):
        return [e for e, _ in self]


def scripted_rng(values):
    it = iter(values)
    return lambda sides: next(it)


class Game:
    """Seam 1: call tools by name against a state tree on a temporary SQLite file, with scripted dice.

    Each Game holds one pooled connection until teardown; a test that makes many Games calls close() on each.
    """

    def __init__(self, factory, template: str, bible: dict | None = None):
        self.factory = factory
        if bible is not None:
            length = "one-shot" if len(bible["acts"]) == 1 else "short"
            self.session_id = start_campaign(factory, Setup("high fantasy", "heroic", length), template, None,
                                             bible=bible).id
        else:
            with factory() as db:
                camp = Campaign(name="Test", premise="A test.")
                create_character(camp, template)
                sess = Session(campaign=camp)
                db.add(camp)
                db.commit()
                self.session_id = sess.id
        self.values: list[int] = []
        self.dice = Dice(rng=self._next)
        self.db = factory()
        self.state = load_state(self.db, self.session_id, self.dice)

    def _next(self, sides: int) -> int:
        assert self.values, f"Scripted dice exhausted (needed a d{sides})"
        v = self.values.pop(0)
        assert 1 <= v <= sides, f"Scripted value {v} impossible on a d{sides}"
        return v

    def script(self, *values: int) -> "Game":
        self.values.extend(values)
        return self

    def random(self, seed: int) -> "Game":
        """Seeded random dice in place of scripted ones, for sweeps where exact rolls don't matter."""
        rnd = _random.Random(seed)
        self.dice.rng = lambda sides: rnd.randint(1, sides)
        return self

    def close(self) -> None:
        self.db.close()

    def call(self, tool: str, /, **args):
        before = len(self.dice.rolls)
        result = dispatch(self.state, tool, args)
        self.last_rolls = self.dice.rolls[before:]
        return result

    def ok(self, tool: str, /, **args):
        result = self.call(tool, **args)
        assert "error" not in result, result
        return result

    @property
    def ch(self):
        return self.state.character

    def commit(self):
        """Commit and reload the state tree from SQLite in a fresh ORM session."""
        turn = self.state.turn
        self.db.commit()
        self.db.close()
        self.db = self.factory()
        self.state = load_state(self.db, self.session_id, self.dice)
        self.state.turn = turn
        return self.state

    def at_turn(self, seq: int) -> "Game":
        """Play the next tool calls as part of Turn `seq`."""
        self.state.turn = seq
        return self

    def combatant(self, name: str):
        return next(c for c in self.state.encounter.combatants if c.name == name)


@pytest.fixture
def factory(tmp_path):
    return open_db(str(tmp_path / "game.sqlite"))


@pytest.fixture
def make_game(factory):
    games = []

    def make(template: str = "fighter", bible: dict | None = None) -> Game:
        g = Game(factory, template, bible)
        games.append(g)
        return g

    yield make
    for g in games:
        g.db.close()


@pytest.fixture(autouse=True)
def auto_roll_by_default(monkeypatch):
    """Tests that don't exercise Roll prompts would wait for a click: new Campaigns start with Auto-roll on.

    A test of a Roll prompt turns it off with `set_auto_roll(factory, False)`.
    """
    monkeypatch.setattr(Campaign.__table__.c.auto_roll, "default", ColumnDefault(True))


def set_auto_roll(factory, on: bool) -> None:
    with factory() as db:
        for camp in db.scalars(select(Campaign)):
            camp.auto_roll = on
        db.commit()
