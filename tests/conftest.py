from __future__ import annotations

import random as _random

import pytest

from pidm.db import open_db
from pidm.dice import Dice
from pidm.engine import load_state
from pidm.models import Campaign, Session
from pidm.templates import create_character
from pidm.tools import dispatch


class Game:
    """Seam 1: call tools by name against a state tree on a temporary SQLite file, with scripted dice.

    Each Game holds one pooled connection until teardown; a test that makes many Games calls close() on each.
    """

    def __init__(self, factory, template: str):
        self.factory = factory
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
        self.db.commit()
        self.db.close()
        self.db = self.factory()
        self.state = load_state(self.db, self.session_id, self.dice)
        return self.state

    def combatant(self, name: str):
        return next(c for c in self.state.encounter.combatants if c.name == name)


@pytest.fixture
def factory(tmp_path):
    return open_db(str(tmp_path / "game.sqlite"))


@pytest.fixture
def make_game(factory):
    games = []

    def make(template: str = "fighter") -> Game:
        g = Game(factory, template)
        games.append(g)
        return g

    yield make
    for g in games:
        g.db.close()
