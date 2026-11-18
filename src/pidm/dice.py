"""Dice: parse expressions such as `2d6+3`, roll them, and record every Roll.

Rolls use the operating system's random source (no fixed seed). Tests inject a
scripted `rng` so results are known in advance.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Callable

_TERM = re.compile(r"([+-]?)\s*(?:(\d*)d(\d+)|(\d+))", re.IGNORECASE)
_EXPR = re.compile(r"^\s*[+-]?\s*(?:\d*d\d+|\d+)(?:\s*[+-]\s*(?:\d*d\d+|\d+))*\s*$", re.IGNORECASE)

MAX_DICE = 100
MAX_SIDES = 1000


class DiceError(ValueError):
    pass


@dataclass
class Roll:
    """One dice result: purpose, expression, the dice rolled, total, target and outcome."""

    purpose: str
    expr: str
    dice: list[int]
    total: int
    target: int | None = None
    outcome: str | None = None

    def as_dict(self) -> dict:
        return {
            "purpose": self.purpose,
            "expr": self.expr,
            "dice": self.dice,
            "total": self.total,
            "target": self.target,
            "outcome": self.outcome,
        }


def parse(expr: str) -> list[tuple[int, int, int]]:
    """Return terms as (sign, count, sides); a flat modifier has sides 0 and count = value."""
    if not isinstance(expr, str) or not _EXPR.match(expr):
        raise DiceError(f"Invalid dice expression: {expr!r}. Use a form like '2d6+3'.")
    terms = []
    for sign, count, sides, flat in _TERM.findall(expr):
        s = -1 if sign == "-" else 1
        if flat:
            terms.append((s, int(flat), 0))
        else:
            n = int(count) if count else 1
            sd = int(sides)
            if not (1 <= n <= MAX_DICE) or not (2 <= sd <= MAX_SIDES):
                raise DiceError(f"Dice out of range in {expr!r}.")
            terms.append((s, n, sd))
    return terms


@dataclass
class Dice:
    """Rolls dice and records each Roll; `on_roll` is called as soon as a Roll is made."""

    rng: Callable[[int], int] | None = None
    on_roll: Callable[[Roll], None] | None = None
    prompt: Callable[[dict], None] | None = None  # asks the player to make the Character's d20 Roll; may block
    rolls: list[Roll] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.rng is None:
            sysrand = random.SystemRandom()
            self.rng = lambda sides: sysrand.randint(1, sides)

    def die(self, sides: int) -> int:
        return self.rng(sides)

    def record(self, roll: Roll) -> Roll:
        self.rolls.append(roll)
        if self.on_roll:
            self.on_roll(roll)
        return roll

    def evaluate(self, expr: str, double_dice: bool = False) -> tuple[list[int], int]:
        """Roll an expression without recording it. `double_dice` rolls every die twice (critical hits)."""
        dice: list[int] = []
        total = 0
        for sign, count, sides in parse(expr):
            if sides == 0:
                total += sign * count
                continue
            for _ in range(count * (2 if double_dice else 1)):
                v = self.die(sides)
                dice.append(v)
                total += sign * v
        return dice, total

    def roll(self, expr: str, purpose: str, target: int | None = None, outcome: str | None = None) -> Roll:
        dice, total = self.evaluate(expr)
        return self.record(Roll(purpose, expr, dice, total, target, outcome))

    def d20(self, mode: str = "normal", lucky: bool = False) -> tuple[list[int], int]:
        """Roll a d20 test. Returns (all dice rolled, kept natural value).

        Advantage/disadvantage roll two and keep one (SRD 5.1 §2.7). Lucky rerolls a
        natural 1 and must use the new roll; with two dice only one die is rerolled (§2.7, §10, R9).
        """
        if mode not in ("normal", "advantage", "disadvantage"):
            raise DiceError(f"Unknown roll mode {mode!r}")
        first = [self.die(20)]
        if mode != "normal":
            first.append(self.die(20))
        dice = list(first)
        kept_pool = list(first)
        if lucky and 1 in kept_pool:
            # R9: always reroll; reroll the one die that matters (one of the 1s).
            idx = kept_pool.index(1)
            new = self.die(20)
            dice.append(new)
            kept_pool[idx] = new
        if mode == "advantage":
            nat = max(kept_pool)
        elif mode == "disadvantage":
            nat = min(kept_pool)
        else:
            nat = kept_pool[0]
        return dice, nat


def combine_modes(advantage: bool, disadvantage: bool) -> str:
    """Any advantage and any disadvantage cancel (SRD 5.1 §2.7)."""
    if advantage and disadvantage:
        return "normal"
    if advantage:
        return "advantage"
    if disadvantage:
        return "disadvantage"
    return "normal"


def scripted(values: list[int]) -> Callable[[int], int]:
    """An rng that returns the given values in order; for tests."""
    it = iter(values)

    def rng(sides: int) -> int:
        try:
            v = next(it)
        except StopIteration:
            raise AssertionError(f"Scripted dice exhausted (needed a d{sides})") from None
        if not 1 <= v <= sides:
            raise AssertionError(f"Scripted value {v} impossible on a d{sides}")
        return v

    return rng
