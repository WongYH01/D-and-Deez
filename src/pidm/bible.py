"""The Campaign bible: Pydantic models for its shape, then the code checks a schema cannot express.

Generated and hand-written bibles pass through the same `validate`.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, ValidationError

Slug = Field(pattern=r"^[a-z0-9][a-z0-9_.-]*$", max_length=60,
             description="Readable unique slug, e.g. act1.beat2, secret.ledger, clue.ledger.1, clock.ritual, loc.mill")

ACTS = {"one-shot": 1, "short": 3}  # Length -> number of Acts


class Beat(BaseModel):
    slug: str = Slug
    goal: str
    requires: list[str] = Field(default_factory=list,
                                description="Slugs of earlier Beats or of Secrets the player must learn first")


class Act(BaseModel):
    slug: str = Slug
    goal: str
    beats: list[Beat] = Field(description="2 to 4 Beats, resolvable in any order unless `requires` says otherwise")


class Secret(BaseModel):
    slug: str = Slug
    act: str = Field(description="Slug of the Act this Secret belongs to")
    revelation: str


class Clue(BaseModel):
    slug: str = Slug
    secret: str = Field(description="Slug of the Secret this Clue points to")
    description: str = Field(description="What the Character finds or hears")
    location: str = Field(description="Slug of the Location where the Clue is placed")


class Clock(BaseModel):
    slug: str = Slug
    name: str
    segments: int = Field(ge=4, le=12)
    consequence: str = Field(description="What happens when the Clock fills")
    main: bool = Field(default=False, description="True for the one Main clock: the antagonist's plan")
    visible: bool = Field(default=False, description="True only if the Character would plainly know about this Clock, "
                          "such as a public countdown; it is then shown to the player. Never true for the Main clock")


class Npc(BaseModel):
    name: str
    motive: str


class Location(BaseModel):
    slug: str = Slug
    name: str
    purpose: str


class Antagonist(BaseModel):
    name: str
    goal: str
    plan: str
    unopposed: str = Field(description="What happens if no one interferes")


class Endings(BaseModel):
    victory: str = Field(description="The Victory condition and how it reads, in prose")
    defeat: str = Field(description="The Defeat condition and how it reads, in prose")


class Bible(BaseModel):
    title: str
    premise: str = Field(description="Spoiler-free premise shown to the player")
    central_question: str
    antagonist: Antagonist
    acts: list[Act]
    secrets: list[Secret]
    clues: list[Clue]
    clocks: list[Clock]
    npcs: list[Npc]
    locations: list[Location]
    start_location: str = Field(description="Slug of the Location where the opening scene takes place")
    endings: Endings
    opening_scene: str = Field(description="Starts mid-action, ties to the backstory hook, ends on a question")


def check(b: Bible, length: str | None) -> list[str]:
    """Human-readable errors for what the schema cannot express; empty when the bible is sound (Story design §2).
    An imported adventure has no chosen length (`None`, or the Campaign's "imported"): it may have 1 to 3 Acts."""
    errors = []
    if length not in ACTS:
        if not 1 <= len(b.acts) <= 3:
            errors.append(f"The bible needs 1 to 3 Acts; it has {len(b.acts)}.")
    elif len(b.acts) != ACTS[length]:
        errors.append(f"A {length} needs {ACTS[length]} Act(s); the bible has {len(b.acts)}.")
    slugs = [x.slug for x in [*b.acts, *(bt for a in b.acts for bt in a.beats), *b.secrets, *b.clues, *b.clocks,
                              *b.locations]]
    dupes = sorted({s for s in slugs if slugs.count(s) > 1})
    if dupes:
        errors.append(f"Duplicate slugs: {', '.join(dupes)}.")
    acts = {a.slug: n for n, a in enumerate(b.acts, 1)}
    locations = {loc.slug for loc in b.locations}
    secrets = {s.slug: s for s in b.secrets}
    if b.start_location not in locations:
        errors.append(f"start_location {b.start_location!r} is not a Location slug.")
    earlier: set[str] = set()
    for n, a in enumerate(b.acts, 1):
        if not 2 <= len(a.beats) <= 4:
            errors.append(f"Act {a.slug} has {len(a.beats)} Beats; each Act needs 2 to 4.")
        for bt in a.beats:
            for r in bt.requires:
                # Only earlier Beats or Secrets of this or an earlier Act, so `requires` can never deadlock an Act.
                if r in secrets:
                    if acts.get(secrets[r].act, 0) > n:
                        errors.append(f"Beat {bt.slug} requires {r}, a Secret of a later Act.")
                elif r not in earlier:
                    errors.append(f"Beat {bt.slug} requires {r!r}, which is neither a Secret nor an earlier Beat.")
            earlier.add(bt.slug)
    for s in b.secrets:
        if s.act not in acts:
            errors.append(f"Secret {s.slug} names Act {s.act!r}, which does not exist.")
        clues = [c for c in b.clues if c.secret == s.slug]
        if len(clues) < 3:
            errors.append(f"Secret {s.slug} has {len(clues)} Clues; it needs at least 3 (Three Clue Rule).")
        if len({c.location for c in clues}) < 2:
            errors.append(f"The Clues of Secret {s.slug} are not spread over at least 2 Locations.")
    for c in b.clues:
        if c.secret not in secrets:
            errors.append(f"Clue {c.slug} points to Secret {c.secret!r}, which does not exist.")
        if c.location not in locations:
            errors.append(f"Clue {c.slug} is placed in Location {c.location!r}, which does not exist.")
    mains = sum(c.main for c in b.clocks)
    if mains != 1:
        errors.append(f"The bible needs exactly one Main clock; it has {mains}.")
    errors += [f"Main clock {c.slug} is visible; the Main clock must stay hidden." for c in b.clocks if c.main and c.visible]
    return errors


def validate(data, length: str | None) -> tuple[Bible | None, list[str]]:
    """Schema first, then the code checks. Returns the bible, or None with the errors."""
    try:
        b = Bible.model_validate(data)
    except ValidationError as e:
        return None, [f"{'.'.join(map(str, err['loc'])) or 'bible'}: {err['msg']}" for err in e.errors()]
    errors = check(b, length)
    return (None if errors else b), errors
