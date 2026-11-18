"""Between-session replanning (design: Story director §5): after a Session's Final recap, one job revises only the
unplayed part of the bible (open Beats, unrevealed Clues, unprogressed side Clocks) and saves it as a new version.

Claude proposes a whole bible; `merge` keeps everything played from the current one, so a proposal cannot touch a
resolved Beat, a revealed Clue, a Secret, an Ending or the Main clock. Replans never overlap a Turn: the next Session's
opening waits in the job queue behind the close job, and no Turn runs while no Session is open.
"""

from __future__ import annotations

import copy
import json
import logging

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from pydantic import ValidationError

from pidm.bible import Bible, validate
from pidm.campaign import ask_bible
from pidm.claude import ClaudeClient
from pidm.prompts import OPENING, RESUME
from pidm.models import Beat, BibleVersion, Campaign, Clock, Clue, Session, Turn

log = logging.getLogger("pidm.replan")

REPLAN_TOOL = "revise_campaign_bible"

REPLAN_SYSTEM = """You revise the hidden Campaign bible of a single-player Dungeons & Dragons 5e game between \
Sessions, so the story fits what the player actually did. Call the revise_campaign_bible tool with the whole bible.

You may change only unplayed content: the open Beats, the unrevealed Clues and the side Clocks that have not \
started filling. Everything else is kept as it is, whatever you send: resolved Beats, revealed Clues, Secrets, \
Acts, Locations, NPCs, the antagonist, the Main clock and the Endings. Change as little as the events require. \
Example: if the player killed an informant, move the Clues he held to other Locations or holders.

Every bible rule still holds: each Secret keeps at least 3 Clues over at least 2 Locations, slugs are unique and \
every reference resolves, each Act keeps 2 to 4 Beats, and Beats may require only earlier Beats or Secrets. Use \
only the Locations already in the bible. Keep the slug of any Beat, Clue or Clock you keep."""


def _played(camp: Campaign) -> tuple[set[str], set[str], set[str]]:
    """Slugs of the resolved Beats, the revealed Clues and the Clocks that must stay as they are."""
    return ({b.slug for b in camp.beats if b.status == "resolved"},
            {c.slug for s in camp.secrets for c in s.clues if c.revealed_turn is not None},
            {c.slug for c in camp.clocks if c.is_main or c.filled > 0})


def merge(current: dict, played: tuple[set[str], set[str], set[str]], proposal: Bible) -> dict:
    """The `current` bible with its unplayed Beats, Clues and Clocks replaced by the proposal's."""
    resolved, revealed, kept_clocks = played
    new = copy.deepcopy(current)
    proposed = {a.slug: a for a in proposal.acts}
    for act in new["acts"]:
        # An Act the proposal drops keeps its open Beats.
        fresh = [b.model_dump() for b in proposed[act["slug"]].beats] if act["slug"] in proposed else act["beats"]
        act["beats"] = [b for b in act["beats"] if b["slug"] in resolved] + [b for b in fresh if b["slug"] not in resolved]
    new["clues"] = [c for c in new["clues"] if c["slug"] in revealed] +         [c.model_dump() for c in proposal.clues if c.slug not in revealed]
    new["clocks"] = [c for c in new["clocks"] if c["slug"] in kept_clocks] +         [c.model_dump() for c in proposal.clocks if c.slug not in kept_clocks]
    return new


def _merged(current: dict, played: tuple[set[str], set[str], set[str]], length: str, data) -> tuple[Bible | None, list[str]]:
    """Merge a proposal (raw tool input) into the current bible and run the bible checks on the result."""
    try:
        proposal = Bible.model_validate(data)
    except ValidationError as e:
        return None, [f"{'.'.join(map(str, err['loc'])) or 'bible'}: {err['msg']}" for err in e.errors()]
    return validate(merge(current, played, proposal), length)


def _items(bible: dict) -> dict[str, dict]:
    return {f"{kind} {x['slug']}": x for kind, xs in (
        ("Beat", [b for a in bible["acts"] for b in a["beats"]]), ("Clue", bible["clues"]), ("Clock", bible["clocks"]))
        for x in xs}


def diff_bibles(old: dict, new: dict) -> str:
    """Plain text of the Beats, Clues and Clocks added, removed or changed; '' when there is no change."""
    a, b = _items(old), _items(new)
    lines = [f"- {k}" for k in a.keys() - b.keys()] + [f"+ {k}: {json.dumps(b[k])}" for k in b.keys() - a.keys()]
    for k in a.keys() & b.keys():
        lines += [f"~ {k}.{f}: {a[k][f]!r} -> {b[k][f]!r}" for f in a[k] if a[k][f] != b[k][f]]
    return "\n".join(sorted(lines))


def apply_bible(camp: Campaign, new: dict, diff: str) -> BibleVersion:
    """Make `new` (from `merge`) the Campaign's bible, with the story rows to match, and save it as the next version."""
    resolved, revealed, kept_clocks = _played(camp)
    bible = Bible.model_validate(new)
    camp.beats = [b for b in camp.beats if b.slug in resolved] + [
        Beat(slug=b.slug, act=n, goal=b.goal, requires=b.requires, status="open")
        for n, act in enumerate(bible.acts, 1) for b in act.beats if b.slug not in resolved]
    for s in camp.secrets:
        s.clues = [c for c in s.clues if c.slug in revealed] + [
            Clue(slug=c.slug, description=c.description, location=c.location)
            for c in bible.clues if c.secret == s.slug and c.slug not in revealed]
    camp.clocks = [c for c in camp.clocks if c.slug in kept_clocks] + [
        Clock(slug=c.slug, name=c.name, segments=c.segments, filled=0, consequence=c.consequence,
              is_main=c.main, visible=c.visible) for c in bible.clocks if c.slug not in kept_clocks]
    camp.bible = new
    version = BibleVersion(version=camp.bible_versions[-1].version + 1, bible=new, diff=diff)
    camp.bible_versions.append(version)
    return version


def _facts(camp: Campaign) -> str:
    return "\n".join(
        f"- {f.subject.name} {f.relation} {f.object.name} (from Turn {f.valid_from_turn}"
        + (f" to Turn {f.valid_to_turn})" if f.valid_to_turn is not None else ")") for f in camp.facts) or "(none)"


def _request(camp: Campaign, recap: str) -> str:
    resolved, revealed, kept = _played(camp)
    clocks = "; ".join(f"{c.slug} {c.filled}/{c.segments}" for c in camp.clocks)
    return (f"Current bible:\n{json.dumps(camp.bible, indent=1, ensure_ascii=False)}\n\n"
            f"Played: Beats resolved: {', '.join(sorted(resolved)) or 'none'}. Clues revealed: "
            f"{', '.join(sorted(revealed)) or 'none'}. Secrets learned: "
            f"{', '.join(s.slug for s in camp.secrets if s.learned_turn is not None) or 'none'}. "
            f"Clocks: {clocks}. Current Act: {camp.current_act}. Location: {camp.current_location}.\n\n"
            f"Facts of the world so far:\n{_facts(camp)}\n\nRecap of the Session just played:\n{recap or '(none)'}")


def replan(factory: sessionmaker, client: ClaudeClient, session_id: int) -> None:
    """The replan job for an ended Session: propose, merge and save a new bible version. A failure, or a proposal that
    changes nothing, keeps the current version and is only logged."""
    with factory() as db:
        sess = db.get(Session, session_id)
        camp = sess.campaign
        played = db.scalar(select(Turn.id).where(Turn.session_id == session_id, Turn.status == "committed",
                                                 Turn.player_text.not_in((OPENING, RESUME))).limit(1))
        if camp.bible is None or camp.status != "active" or played is None:
            return  # no story left to adapt, or the player did nothing
        request, base = _request(camp, sess.final_recap or sess.rolling_recap), camp.bible_versions[-1].version
        current, played, length = camp.bible, _played(camp), camp.length
    try:
        bible = ask_bible(client, REPLAN_SYSTEM, request, REPLAN_TOOL, lambda data: _merged(current, played, length, data))
    except Exception:
        log.exception("Replan after Session %s failed; keeping the current bible", session_id)
        return
    with factory() as db:
        camp = db.get(Session, session_id).campaign
        if camp.bible_versions[-1].version != base:
            return  # rolled back or replanned meanwhile
        new = bible.model_dump()  # already merged and checked; no Turn can have changed the story since
        diff = diff_bibles(camp.bible, new)
        if not diff:
            return
        version = apply_bible(camp, new, diff)
        db.commit()
        log.info("Campaign %s adapted to bible version %s:\n%s", camp.id, version.version, diff)


def rollback(factory: sessionmaker, campaign_id: int, version: int) -> None:
    """Make an earlier version's unplayed content current again, as a new version; played content stays as played.
    Call it only while no Turn is running."""
    with factory() as db:
        camp = db.get(Campaign, campaign_id)
        old = next((v for v in camp.bible_versions if v.version == version), None)
        if old is None:
            raise ValueError(f"Campaign {campaign_id} has no bible version {version}.")
        merged, errors = _merged(camp.bible, _played(camp), camp.length, old.bible)
        if merged is None:
            raise ValueError(f"Version {version} no longer fits the story: {'; '.join(errors)}")
        new = merged.model_dump()
        apply_bible(camp, new, f"Rolled back to version {version}.\n{diff_bibles(camp.bible, new)}")
        db.commit()
