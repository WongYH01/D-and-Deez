"""World memory: Entities, Facts and DM notes, and the context blocks they feed (design: Memory strategy).

Memory tools take names, validate against the Turn's state tree and change only the tree (ADR 0002).
"""

from __future__ import annotations

import re

from pidm.bible import Bible
from pidm.engine import GameState, ToolError
from pidm.models import Campaign, DmNote, Entity, Fact

KINDS = ("npc", "place", "faction", "item")
NOTE_CAP_CHARS = 2000  # about 500 tokens at the engine's characters / 4 estimate
HOPS = 2  # Memory strategy: Facts within 2 hops of the Entities the context names
MIN_ALIAS = 4  # Memory strategy: aliases shorter than this are skipped
# Memory strategy: a stop list of aliases too common to name anyone.
STOP_WORDS = {"them", "then", "this", "that", "with", "from", "what", "when", "your", "have", "will", "there", "here"}


def seed_entities(camp: Campaign, bible: Bible) -> None:
    """NPCs and Locations of the bible become Entities; Location stays bible-only (`location_slug`)."""
    for n in bible.npcs:
        # The part before a comma and its words name the NPC too ("Mira, Osric's widow" is "Mira").
        short = n.name.split(",")[0].strip()
        aliases = [x for x in dict.fromkeys([short, *short.split()]) if x != n.name and len(x) >= MIN_ALIAS]
        camp.entities.append(Entity(name=n.name, kind="npc", aliases=aliases, summary=n.motive))
    for loc in bible.locations:
        camp.entities.append(Entity(name=loc.name, kind="place", aliases=[], summary=loc.purpose,
                                    location_slug=loc.slug))


def _find(camp: Campaign, name: str) -> Entity | None:
    key = name.strip().lower()
    return next((e for e in camp.entities if key in [e.name.lower(), *(a.lower() for a in e.aliases)]), None)


def _entity(state: GameState, name: str, kind: str | None, role: str) -> Entity:
    """The Entity called `name`; an unknown name needs its `kind` and is created."""
    if not name.strip():
        raise ToolError(f"{role} must not be empty.")
    found = _find(state.campaign, name)
    if found:
        return found
    if kind is None:
        raise ToolError(f"No Entity named {name!r}. Give {role}_kind ({', '.join(KINDS)}) to add it.")
    if kind not in KINDS:
        raise ToolError(f"{role}_kind must be one of {list(KINDS)}.")
    return Entity(name=name.strip(), kind=kind, aliases=[])


def t_add_fact(state: GameState, subject: str, relation: str, object: str,
               subject_kind: str | None = None, object_kind: str | None = None) -> dict:
    camp = state.campaign
    if not relation.strip() or len(relation.strip()) > 100:
        raise ToolError("relation must be 1 to 100 characters.")
    subj = _entity(state, subject, subject_kind, "subject")
    obj = _entity(state, object, object_kind, "object")
    if subj.name.lower() == obj.name.lower():
        raise ToolError("A Fact relates two different Entities; an Entity cannot relate to itself.")
    rel = relation.strip()
    for f in camp.facts:
        if f.valid_to_turn is None and f.subject is subj and f.object is obj and f.relation.lower() == rel.lower():
            raise ToolError(f"Fact {f.id} already holds: {subj.name} {f.relation} {obj.name}.")
    for e in (subj, obj):
        if e.id is None and e not in camp.entities:
            camp.entities.append(e)
    fact = Fact(subject=subj, relation=rel, object=obj, valid_from_turn=state.turn, source_turn=state.turn)
    camp.facts.append(fact)
    state.db.flush()
    return {"fact_id": fact.id, "fact": f"{subj.name} {rel} {obj.name}"}


def t_retire_fact(state: GameState, fact_id: int) -> dict:
    fact = next((f for f in state.campaign.facts if f.id == fact_id), None)
    if fact is None:
        raise ToolError(f"No Fact {fact_id}. Current Facts are listed in <world>.")
    if fact.valid_to_turn is not None:
        raise ToolError(f"Fact {fact_id} is already retired.")
    fact.valid_to_turn = state.turn
    return {"retired": fact_id}


def t_write_note(state: GameState, note: str, note_id: int | None = None) -> dict:
    """Add a note, or with note_id replace it; an empty note deletes it. At the cap nothing is trimmed (issue #28)."""
    camp = state.campaign
    old = None
    if note_id is not None:
        old = next((n for n in camp.dm_notes if n.id == note_id), None)
        if old is None:
            raise ToolError(f"No note {note_id}.")
    note = note.strip()
    if old is not None and not note:
        camp.dm_notes.remove(old)
        return {"deleted": note_id}
    if not note:
        raise ToolError("note must not be empty.")
    used = sum(len(n.note) for n in camp.dm_notes if n is not old) + len(note)
    if used > NOTE_CAP_CHARS:
        ids = ", ".join(str(n.id) for n in camp.dm_notes)
        raise ToolError(f"DM notes are over the cap ({used} of {NOTE_CAP_CHARS} characters). Update or delete an "
                        f"older note first (write_note with note_id, empty note to delete). Notes: {ids}.")
    if old is not None:
        old.note, old.updated_turn = note, state.turn
        return {"note_id": old.id}
    new = DmNote(note=note, updated_turn=state.turn)
    camp.dm_notes.append(new)
    state.db.flush()
    return {"note_id": new.id}


def _mentioned(camp: Campaign, texts: list[str]) -> set[int]:
    body = "\n".join(texts)
    out = set()
    for e in camp.entities:
        for n in [e.name, *(a for a in e.aliases if len(a) >= MIN_ALIAS and a.lower() not in STOP_WORDS)]:
            if re.search(rf"(?<!\w){re.escape(n)}(?!\w)", body, re.I):
                out.add(e.id)
                break
    return out


def memory_blocks(state: GameState, texts: list[str], hops: int = HOPS) -> tuple[str, str]:
    """The <world> and <notes> bodies ('' when empty): current Facts within `hops` of the Entities `texts` name or of
    the current Location, and every DM note."""
    camp = state.campaign
    reached = _mentioned(camp, texts) | {e.id for e in camp.entities
                                         if e.location_slug and e.location_slug == camp.current_location}
    current = [f for f in camp.facts if f.valid_to_turn is None]
    shown: dict[int, Fact] = {}
    for _ in range(hops):
        step = [f for f in current if f.subject_id in reached or f.object_id in reached]
        shown.update((f.id, f) for f in step)
        reached |= {f.subject_id for f in step} | {f.object_id for f in step}
    world = "\n".join(f"- [{f.id}] {f.subject.name} {f.relation} {f.object.name}" for f in shown.values())
    notes = "\n".join(f"- [{n.id}] {n.note}" for n in camp.dm_notes)
    return world, notes
