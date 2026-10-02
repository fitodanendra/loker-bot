"""Bookkeeping for jobs already sent, so nothing is notified twice."""

from datetime import datetime, timedelta
from typing import Iterable

from loker_bot.dates import parse_iso

Seen = dict[str, str]


def with_seen(seen: Seen, uids: Iterable[str], now: datetime) -> Seen:
    return {**seen, **{uid: now.isoformat() for uid in uids}}


def prune_seen(seen: Seen, now: datetime, keep_days: int) -> Seen:
    cutoff = now - timedelta(days=keep_days)
    return {
        uid: stamp for uid, stamp in seen.items()
        if (parse_iso(stamp) or now) >= cutoff
    }
