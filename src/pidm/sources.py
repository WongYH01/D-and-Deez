"""Adventure import: extract text locally, store it, convert it to a bible, retrieve it per Location (design:
Adventure import).

Uploaded files stay on this machine: the file under the sources folder, its text split into `source_chunks`. Claude
sees the text only inside the conversion request and, per Location, in a Turn's context; the UI never shows it.
"""

from __future__ import annotations

import hashlib
import io
import re
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession, sessionmaker

from pidm.bible import Bible
from pidm.models import Source

MAX_CHARS = 400_000  # about 100k tokens: the whole text goes to Claude once, to convert it
CHUNK_CHARS = 3000  # a longer section is split at paragraph breaks
RETRIEVED_CHARS = 6000  # cap on source text in one Turn's context
PARTY_WARNING = ("Published adventures assume a party of four or five. One Character will find it harder, and "
                 "this release does no solo scaling.")


class SourceError(Exception):
    """The upload cannot be imported; the message is shown to the player."""


def extract_text(filename: str, data: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader
        from pypdf.errors import PyPdfError
        try:
            body = "\n\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(data)).pages)
        except (PyPdfError, ValueError, KeyError) as e:
            raise SourceError(f"That PDF could not be read ({e}).") from e
        if not body.strip():
            raise SourceError("That PDF has no text layer (a scan?). Run OCR on it, or upload a text file.")
    elif suffix in (".txt", ".md", ".markdown"):
        try:
            body = data.decode("utf-8-sig")
        except UnicodeDecodeError as e:
            raise SourceError("That file is not UTF-8 text.") from e
        if not body.strip():
            raise SourceError("That file is empty.")
    else:
        raise SourceError("Upload a PDF, Markdown or text file.")
    if len(body) > MAX_CHARS:
        raise SourceError(f"That adventure is too long to import ({len(body):,} characters; the limit is {MAX_CHARS:,}).")
    return body


_HEADING = re.compile(r"^(#{1,6}\s+.+|[A-Z0-9][A-Z0-9 '&,:.-]{2,59})$")  # a Markdown heading, or a short ALL CAPS line


def split_chunks(body: str) -> list[tuple[str, str]]:
    """(heading, text) pairs: a new chunk at each heading line, long ones cut at paragraph breaks."""
    chunks: list[tuple[str, list[str]]] = [("", [])]
    for line in body.splitlines():
        if _HEADING.match(line.strip()):
            chunks.append((line.strip().lstrip("#").strip(), []))
        else:
            chunks[-1][1].append(line)
    out = []
    for heading, lines in chunks:
        part = ""
        for para in re.split(r"\n\s*\n", "\n".join(lines).strip()):
            if part and len(part) + len(para) > CHUNK_CHARS:
                out.append((heading, part))
                part = ""
            part = f"{part}\n\n{para}" if part else para
        if part.strip():
            out.append((heading, part.strip()))
    return out


def store_source(factory: sessionmaker, folder: Path, filename: str, data: bytes) -> int:
    """Extract, save the file and its chunks; returns the Source id. Raises SourceError for a bad upload."""
    body = extract_text(filename, data)
    folder.mkdir(parents=True, exist_ok=True)
    with factory() as db:
        src = Source(title=Path(filename).stem[:200], sha256=hashlib.sha256(data).hexdigest())
        db.add(src)
        db.flush()
        path = folder / f"{src.id}{Path(filename).suffix.lower()}"
        path.write_bytes(data)
        src.path = str(path)
        for heading, chunk in split_chunks(body):
            db.execute(text("INSERT INTO source_chunks (heading, body, kind, ref, source_id) "
                            "VALUES (:h, :b, 'section', '', :s)"), {"h": heading, "b": chunk, "s": src.id})
        db.commit()
        return src.id


def delete_source(factory: sessionmaker, source_id: int) -> None:
    with factory() as db:
        src = db.get(Source, source_id)
        if src is None:
            return
        db.execute(text("DELETE FROM source_chunks WHERE source_id = :s"), {"s": source_id})
        if src.path:
            Path(src.path).unlink(missing_ok=True)
        db.delete(src)
        db.commit()


def _chunks(db: DbSession, source_id: int) -> list[tuple[int, str, str]]:
    return [tuple(r) for r in db.execute(text("SELECT rowid, heading, body FROM source_chunks WHERE source_id = :s "
                                              "ORDER BY rowid"), {"s": source_id})]


def full_text(db: DbSession, source_id: int) -> str:
    return "\n\n".join(f"## {h}\n{b}" if h else b for _, h, b in _chunks(db, source_id))


def tag_chunks(db: DbSession, source_id: int, bible: Bible) -> None:
    """Tie each chunk to the bible Location its heading names (kind `location`) or to an NPC (kind `npc`, ref the
    name); anything else stays a `section` with no ref."""
    db.execute(text("UPDATE source_chunks SET kind = 'section', ref = '' WHERE source_id = :s"), {"s": source_id})
    for rowid, heading, _ in _chunks(db, source_id):
        key = heading.lower()
        loc = next((x for x in bible.locations if key and x.name.lower() in key), None)
        npc = next((n for n in bible.npcs if key and n.name.split(",")[0].strip().lower() in key), None)
        if loc or npc:
            db.execute(text("UPDATE source_chunks SET kind = :k, ref = :r WHERE rowid = :i"),
                       {"k": "location" if loc else "npc", "r": loc.slug if loc else npc.name, "i": rowid})


def location_text(db: DbSession, source_id: int, location: str) -> str:
    """The author's text for a Location, capped; empty when none is tagged."""
    rows = db.execute(text("SELECT heading, body FROM source_chunks WHERE source_id = :s AND kind = 'location' "
                           "AND ref = :r ORDER BY rowid"), {"s": source_id, "r": location})
    out = "\n\n".join(f"{h}\n{b}" if h else b for h, b in rows)
    return out[:RETRIEVED_CHARS]


IMPORT_SYSTEM = """You convert a published Dungeons & Dragons 5e adventure into a hidden Campaign bible for a \
single-player game (SRD 5.1). The player never sees the bible; they see only its spoiler-free premise. Call the \
write_campaign_bible tool with the whole bible.

Keep the author's story: map its chapters or areas to Acts and Beats, its areas to Locations (use the author's \
area names as Location names, so their text can be found again), its characters to NPCs, its revelations to Secrets \
and Clues, and its hook to the opening scene. One Act for a one-shot, up to three for a longer adventure.

Fill the gaps the author left, and the code will check every one:
- Each Act has 2 to 4 Beats. A Beat may list in `requires` earlier Beats (listed before it) or Secrets of its own or \
an earlier Act.
- Three Clue Rule: every Secret has at least 3 Clues spread over at least 2 different Locations; add Clues in other \
Locations where the author gave fewer.
- Exactly one hidden Main clock (main: true, 4 to 12 segments) for the antagonist's plan, added if the author has \
none. Endings: a Victory and a Defeat (the Main clock fills first), added if the author has none.
- Every slug is unique and every slug reference resolves.
- The premise must be spoiler-free.
- Never include anything on the Lines list; keep anything on the Veils list off-screen.
"""
