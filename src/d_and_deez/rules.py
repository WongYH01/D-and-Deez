"""Rule section search over rules_fts, for lookup_rule and keyword retrieval into the Turn's context."""

from __future__ import annotations

import re

from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

# Rules a player action can name: FTS term -> word forms in the action. Add a trigger with one line.
RULE_KEYWORDS = {
    "grapple": r"grappl\w*",
    "shove": r"shov\w*",
    "hide": r"hide|hides|hiding|hidden",
    "cover": r"cover|covers|covered|covering",
    "opportunity attack": r"opportunity attacks?",
    "dodge": r"dodg\w*",
    "disengage": r"disengag\w*",
    "help": r"help|helps|helping|aid|aids|aiding",
    "ready": r"ready|readies|readied|readying",
    "rest": r"rest|rests|rested|resting",
    "dash": r"dash|dashes|dashing",
    "search": r"search|searches|searching",
    "climb": r"climb\w*",
    "swim": r"swim|swims|swimming|swam",
    "jump": r"jump\w*|leap\w*",
    "fall": r"fall|falls|falling|fell|fallen",
    "prone": r"prone",
    "squeeze": r"squeez\w*",
    "mounted": r"mount|mounts|mounted|mounting|ride|rides|riding",
    "underwater": r"underwater",
    "suffocating": r"suffocat\w*|drown\w*",
    "two-weapon fighting": r"two-weapon|dual[- ]wield\w*",
}
_KEYWORD_RE = {k: re.compile(rf"\b(?:{v})\b", re.IGNORECASE) for k, v in RULE_KEYWORDS.items()}

RETRIEVED = 2
CAP_CHARS = 2400  # about 600 tokens at 4 characters per token
CUT_NOTE = "[Cut for length; lookup_rule returns the full text.]"


def search(db: DbSession, terms: list[str], limit: int) -> list[dict]:
    """Top Rule sections matching any term, ranked by BM25 with heading matches weighted up."""
    if not terms:
        return []
    query = " OR ".join('"' + t.replace('"', "") + '"' for t in terms)
    rows = db.execute(text("SELECT section, body FROM rules_fts WHERE rules_fts MATCH :q "
                           "ORDER BY bm25(rules_fts, 10.0, 1.0) LIMIT :n"), {"q": query, "n": limit})
    return [{"section": s, "body": b} for s, b in rows]


def lookup(db: DbSession, query: str, limit: int = 3) -> list[dict]:
    return search(db, re.findall(r"\w+", query.lower()), limit)


def retrieve(db: DbSession, player_text: str) -> list[dict]:
    """Rule sections the player's action names, capped; no keyword means no query at all."""
    terms = [k for k, rx in _KEYWORD_RE.items() if rx.search(player_text)]
    out = []
    for r in search(db, terms, RETRIEVED):
        if len(r["body"]) > CAP_CHARS:
            r["body"] = r["body"][:CAP_CHARS].rsplit(" ", 1)[0] + " " + CUT_NOTE
        out.append(r)
    return out
