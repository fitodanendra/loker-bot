import json
from pathlib import Path

from loker_bot.models import Search, Settings

DEFAULT_MAX_AGE_HOURS = 48


class ConfigError(ValueError):
    pass


def load_config(path: Path) -> tuple[list[Search], Settings]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ConfigError(f"Cannot read config {path}: {error}") from error

    searches = [_parse_search(item) for item in raw.get("searches") or []]
    if not searches:
        raise ConfigError("config.json must contain at least one entry in 'searches'")

    max_age = raw.get("max_age_hours", DEFAULT_MAX_AGE_HOURS)
    if not isinstance(max_age, int) or max_age <= 0:
        raise ConfigError("'max_age_hours' must be a positive integer")

    settings = Settings(
        locations=_str_tuple(raw.get("locations"), "locations"),
        include_remote=bool(raw.get("include_remote", True)),
        max_age_hours=max_age,
    )
    return searches, settings


def _parse_search(item) -> Search:
    query = item.get("query") if isinstance(item, dict) else None
    if not isinstance(query, str) or not query.strip():
        raise ConfigError(f"Each search needs a non-empty 'query': {item!r}")
    name = item.get("name") or query
    if not isinstance(name, str):
        raise ConfigError(f"'name' must be a string: {item!r}")
    return Search(
        query=query.strip(),
        title_must_include=_str_tuple(item.get("title_must_include"), "title_must_include"),
        name="".join(name.lower().split()),
    )


def _str_tuple(value, field: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ConfigError(f"'{field}' must be a list of strings")
    return tuple(value)
