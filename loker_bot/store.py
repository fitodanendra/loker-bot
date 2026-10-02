"""Remembers which jobs were already sent, so nothing is notified twice."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

from loker_bot.dates import parse_iso

log = logging.getLogger(__name__)

Seen = dict[str, str]


def load_seen(path: Path) -> Seen:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        log.warning("Could not read %s (%s); starting with empty history", path, error)
        return {}
    return data if isinstance(data, dict) else {}


def save_seen(path: Path, seen: Seen) -> None:
    path.write_text(json.dumps(seen, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def with_seen(seen: Seen, uids: Iterable[str], now: datetime) -> Seen:
    return {**seen, **{uid: now.isoformat() for uid in uids}}


def prune_seen(seen: Seen, now: datetime, keep_days: int) -> Seen:
    cutoff = now - timedelta(days=keep_days)
    return {
        uid: stamp for uid, stamp in seen.items()
        if (parse_iso(stamp) or now) >= cutoff
    }
