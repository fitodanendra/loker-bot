"""User preferences chosen from Telegram (stored by the Cloudflare Worker)."""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from loker_bot.models import Search

log = logging.getLogger(__name__)

Custom = dict[str, str]  # category name -> search keyword


@dataclass(frozen=True)
class Prefs:
    active: frozenset[str]
    custom: Custom = field(default_factory=dict)
    locations: Optional[tuple[str, ...]] = None  # None = config.json; () = all of Indonesia


def prefs_from_dict(raw: Any, categories: tuple[str, ...]) -> Prefs:
    default = Prefs(active=frozenset(categories))
    if raw is None:
        return default
    try:
        custom = {str(name): str(keyword) for name, keyword in (raw.get("custom") or {}).items()}
        known = frozenset(categories) | frozenset(custom)
        active = raw.get("active") or []
        if not isinstance(active, list):
            raise TypeError("'active' must be a list")
        locations = raw.get("locations")
        return Prefs(
            active=frozenset(active) & known or known,
            custom=custom,
            locations=None if locations is None else tuple(str(place) for place in locations),
        )
    except (AttributeError, TypeError, ValueError) as error:
        log.warning("Ignoring malformed prefs (%s); using defaults", error)
        return default


def active_searches(searches: list[Search], active: frozenset[str]) -> list[Search]:
    chosen = [search for search in searches if search.name in active]
    return chosen or searches


def custom_searches(custom: Custom) -> list[Search]:
    return [
        Search(query=keyword, name=name, title_must_include_all=tuple(keyword.split()))
        for name, keyword in custom.items()
    ]
