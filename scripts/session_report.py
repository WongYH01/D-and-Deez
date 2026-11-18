"""Session report for the v1 release check (#20): cost per 30 minutes, then the Turn and Roll log.

Reads the SQLite file directly (stdlib only; run it on the host or on a copy of the DB):
    python scripts/session_report.py --db data/d-and-deez.sqlite [--session 3] [--no-log] [--bucket 30]

Cost covers Turn calls only (narration and tools). Recap and bible-planning calls store no tokens, so they are
not counted; the Haiku recap is small. Prices are USD per million tokens (Sonnet 5.5 defaults); override with flags.
Turns store input as one number (cache creation included), so cache writes are billed at the plain input rate here
and the total runs slightly low.
"""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime, timedelta


def cost(tokens_in: int, tokens_out: int, tokens_cached: int, p_in: float, p_out: float, p_cache: float) -> float:
    return ((tokens_in - tokens_cached) * p_in + tokens_cached * p_cache + tokens_out * p_out) / 1e6


def buckets(turns: list[dict], start: datetime, minutes: int, prices: tuple[float, float, float]) -> list[dict]:
    """Group Turns into windows of `minutes` from `start`; each row has turns, tokens and USD."""
    rows: dict[int, dict] = {}
    for t in turns:
        n = int((t["created_at"] - start) / timedelta(minutes=minutes))
        r = rows.setdefault(n, {"window": n, "turns": 0, "tokens_in": 0, "tokens_out": 0, "tokens_cached": 0, "usd": 0.0})
        r["turns"] += 1
        r["tokens_in"] += t["tokens_in"]
        r["tokens_out"] += t["tokens_out"]
        r["tokens_cached"] += t["tokens_cached"]
        r["usd"] += cost(t["tokens_in"], t["tokens_out"], t["tokens_cached"], *prices)
    return [rows[k] for k in sorted(rows)]


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/d-and-deez.sqlite")
    ap.add_argument("--session", type=int, help="Session id (default: the latest)")
    ap.add_argument("--bucket", type=int, default=30, help="minutes per cost row")
    ap.add_argument("--no-log", action="store_true", help="cost table only")
    ap.add_argument("--price-in", type=float, default=2.0)
    ap.add_argument("--price-out", type=float, default=10.0)
    ap.add_argument("--price-cache-read", type=float, default=0.10)
    a = ap.parse_args()

    db = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    s = db.execute("SELECT * FROM sessions WHERE id = ?" if a.session else "SELECT * FROM sessions ORDER BY id DESC LIMIT 1",
                   (a.session,) if a.session else ()).fetchone()
    if s is None:
        raise SystemExit("no such Session")
    turns = [dict(r, created_at=_ts(r["created_at"])) for r in
             db.execute("SELECT * FROM turns WHERE session_id = ? ORDER BY seq", (s["id"],))]
    start = _ts(s["started_at"])
    prices = (a.price_in, a.price_out, a.price_cache_read)

    print(f"Session {s['id']} (Campaign {s['campaign_id']}) started {s['started_at']}, ended {s['ended_at'] or '-'}")
    print(f"\n{'window':<12}{'turns':>6}{'in':>10}{'cached':>10}{'out':>8}{'USD':>9}{'running':>9}")
    running = 0.0
    for r in buckets(turns, start, a.bucket, prices):
        running += r["usd"]
        lo = r["window"] * a.bucket
        print(f"{lo:>3}-{lo + a.bucket:<3} min {r['turns']:>6}{r['tokens_in']:>10}{r['tokens_cached']:>10}"
              f"{r['tokens_out']:>8}{r['usd']:>9.3f}{running:>9.3f}")
    print(f"Total ${running:.3f} over {len(turns)} Turns (Turn calls only)")
    if a.no_log:
        return

    print("\n--- Turn and Roll log ---")
    for t in turns:
        print(f"\n#{t['seq']} [{t['status']}] {t['created_at']:%H:%M:%S}\n> {t['player_text']}")
        for r in db.execute("SELECT * FROM rolls WHERE turn_id = ? ORDER BY seq", (t["id"],)):
            print(f"  roll: {r['purpose']} {r['expr']} -> {r['total']}"
                  + (f" vs {r['target']}" if r["target"] is not None else "") + (f" ({r['outcome']})" if r["outcome"] else ""))
        print(t["narration"])


if __name__ == "__main__":
    main()
