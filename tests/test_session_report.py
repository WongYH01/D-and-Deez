import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from session_report import buckets, cost  # noqa: E402


def test_cost_bills_cached_input_at_the_cache_rate():
    # 1M input of which 400k cached, 100k output at $2 / $10 / $0.10
    assert cost(1_000_000, 100_000, 400_000, 2.0, 10.0, 0.10) == 1.2 + 0.04 + 1.0


def test_buckets_group_turns_into_30_minute_windows():
    t0 = datetime(2026, 1, 1, 20, 0)
    turn = lambda m: dict(created_at=t0 + timedelta(minutes=m), tokens_in=1_000_000, tokens_out=0, tokens_cached=0)
    rows = buckets([turn(1), turn(29), turn(61)], t0, 30, (2.0, 10.0, 0.1))
    assert [(r["window"], r["turns"], r["usd"]) for r in rows] == [(0, 2, 4.0), (2, 1, 2.0)]
