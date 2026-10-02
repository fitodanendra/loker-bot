"""Reads chat commands sent to the bot and stores the chosen categories in prefs.json."""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from loker_bot.commands import handle_command
from loker_bot.custom import Custom, handle_custom_command
from loker_bot.models import Search

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Prefs:
    active: frozenset[str]
    last_update_id: int
    custom: Custom = field(default_factory=dict)


def process_updates(
    updates: list[dict], owner_chat_id: str, categories: tuple[str, ...], prefs: Prefs,
) -> tuple[Prefs, list[str]]:
    active = prefs.active
    custom = prefs.custom
    last_id = prefs.last_update_id
    replies = []
    for item in updates:
        last_id = max(last_id, int(item.get("update_id", 0)))
        message = item.get("message") or {}
        text = message.get("text")
        if not text or str((message.get("chat") or {}).get("id")) != owner_chat_id:
            continue
        result = handle_custom_command(text, categories, custom, active)
        if result is None:
            active, reply = handle_command(text, categories + tuple(custom), active)
        else:
            custom, active, reply = result
        replies.append(reply)
    return Prefs(active=active, last_update_id=last_id, custom=custom), replies


def active_searches(searches: list[Search], active: frozenset[str]) -> list[Search]:
    chosen = [search for search in searches if search.name in active]
    return chosen or searches


def load_prefs(path: Path, categories: tuple[str, ...]) -> Prefs:
    default = Prefs(active=frozenset(categories), last_update_id=0)
    if not path.exists():
        return default
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        custom = {str(name): str(keyword) for name, keyword in (raw.get("custom") or {}).items()}
        known = frozenset(categories) | frozenset(custom)
        return Prefs(
            active=frozenset(raw["active"]) & known or known,
            last_update_id=int(raw.get("last_update_id", 0)),
            custom=custom,
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        log.warning("Could not read %s (%s); using all categories", path, error)
        return default


def save_prefs(path: Path, prefs: Prefs) -> None:
    data = {
        "active": sorted(prefs.active),
        "custom": prefs.custom,
        "last_update_id": prefs.last_update_id,
    }
    path.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
