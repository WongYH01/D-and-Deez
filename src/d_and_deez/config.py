"""Every environment read goes through `env`, so dropping the PIDM_ fallback later is a one-place change."""

from __future__ import annotations

import os

DEFAULT_DB = "data/d-and-deez.sqlite"
LEGACY_DB = "data/pidm.sqlite"


def env(name: str, default: str | None = None) -> str | None:
    """DND_<name>, else PIDM_<name>, else the default."""
    # shortcut: PIDM_ names are read for one release so an existing .env keeps working; remove them next release.
    for prefix in ("DND_", "PIDM_"):
        value = os.environ.get(prefix + name)
        if value is not None:
            return value
    return default


def db_path() -> str:
    """The SQLite path: DND_DB or PIDM_DB if set, else data/d-and-deez.sqlite, else an existing data/pidm.sqlite."""
    path = env("DB")
    if path is not None:
        return path
    # shortcut: an old data/pidm.sqlite is still opened when the new default file is absent; remove with the PIDM_ fallback.
    if not os.path.exists(DEFAULT_DB) and os.path.exists(LEGACY_DB):
        return LEGACY_DB
    return DEFAULT_DB
