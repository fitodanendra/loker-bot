"""Entry point: search every source, filter, notify new jobs on Telegram.

Usage:
    python -m loker_bot.main            # send to Telegram
    python -m loker_bot.main --dry-run  # only print what would be sent
"""

import logging
from dataclasses import replace
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from typing import Callable

from loker_bot.config import ConfigError, load_config
from loker_bot.filters import is_wanted
from loker_bot.prefs import active_searches, custom_searches, prefs_from_dict
from loker_bot.models import Job, Search, Settings
from loker_bot.sources import dealls, jobstreet, kalibrr, linkedin
from loker_bot.state import State, StateClient, StateError
from loker_bot.store import Seen, prune_seen, with_seen
from loker_bot.telegram import TelegramClient, format_message

log = logging.getLogger("loker_bot")

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"
MAX_PER_RUN = 25
KEEP_SEEN_DAYS = 7  # longer than config max_age_hours, so old jobs are never re-sent
SECONDS_BETWEEN_MESSAGES = 1.1

SourceFn = Callable[[str], list[Job]]
SendFn = Callable[[Job, str], None]

SOURCES: dict[str, SourceFn] = {
    "JobStreet": jobstreet.search,
    "Kalibrr": kalibrr.search,
    "LinkedIn": linkedin.search,
    "Dealls": dealls.search,
}


def collect_new_jobs(
    searches: list[Search], settings: Settings, seen: Seen,
    sources: dict[str, SourceFn], now: datetime,
) -> list[tuple[Job, str]]:
    found: dict[str, tuple[Job, str]] = {}
    for search in searches:
        for name, fetch in sources.items():
            for job in _safe_fetch(name, fetch, search.query):
                if job.uid in seen or job.uid in found:
                    continue
                if is_wanted(job, search, settings, now):
                    found[job.uid] = (job, search.query)
    oldest = datetime.min.replace(tzinfo=timezone.utc)
    return sorted(found.values(), key=lambda pair: pair[0].posted_at or oldest)


def _safe_fetch(name: str, fetch: SourceFn, query: str) -> list[Job]:
    try:
        return fetch(query)
    except Exception as error:  # one broken source must not stop the others
        log.warning("%s search for %r failed: %s", name, query, error)
        return []


def notify(
    jobs: list[tuple[Job, str]], seen: Seen, send: SendFn, now: datetime, max_per_run: int,
) -> Seen:
    sent_uids = []
    for job, query in jobs[:max_per_run]:
        try:
            send(job, query)
        except Exception as error:
            log.error("Failed to send %s: %s", job.uid, error)
            continue
        sent_uids.append(job.uid)
    if len(jobs) > max_per_run:
        log.info("%d more jobs will be sent next run", len(jobs) - max_per_run)
    return with_seen(seen, sent_uids, now)


def _telegram_client() -> TelegramClient:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        raise ConfigError("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables")
    return TelegramClient(token, chat_id)


def _telegram_sender(client: TelegramClient) -> SendFn:
    def send(job: Job, query: str) -> None:
        client.send_job(job, query)
        time.sleep(SECONDS_BETWEEN_MESSAGES)

    return send


def _print_sender(job: Job, query: str) -> None:
    print(format_message(job, query), f"\n🔗 {job.url}\n")


def _state_client(required: bool) -> Optional[StateClient]:
    url = os.environ.get("STATE_URL", "").strip()
    secret = os.environ.get("STATE_SECRET", "").strip()
    if url and secret:
        return StateClient(url, secret)
    if required:
        raise ConfigError("Set STATE_URL and STATE_SECRET environment variables")
    return None


def run(dry_run: bool) -> int:
    now = datetime.now(timezone.utc)
    try:
        searches, settings = load_config(CONFIG_PATH)
        state_client = _state_client(required=not dry_run)
        send = _print_sender if dry_run else _telegram_sender(_telegram_client())
    except ConfigError as error:
        log.error("%s", error)
        return 1

    try:
        state = state_client.load() if state_client else State(prefs_raw=None, seen={}, config=None)
    except StateError as error:
        # Without the sent-job history every job would be sent again, so stop here.
        log.error("%s", error)
        return 1

    categories = tuple(search.name for search in searches)
    config = {"builtin": list(categories), "default_locations": list(settings.locations)}
    prefs = prefs_from_dict(state.prefs_raw, categories)
    if prefs.locations is not None:
        settings = replace(settings, locations=prefs.locations)
    chosen = active_searches(searches + custom_searches(prefs.custom), prefs.active)
    log.info("Active categories: %s", ", ".join(search.name for search in chosen))
    log.info("Locations: %s", ", ".join(settings.locations) or "all of Indonesia")

    seen = prune_seen(state.seen, now, KEEP_SEEN_DAYS)
    jobs = collect_new_jobs(chosen, settings, seen, SOURCES, now)
    log.info("Found %d new matching jobs", len(jobs))
    updated = notify(jobs, seen, send, now, MAX_PER_RUN)

    if dry_run:
        return 0
    try:
        state_client.save(
            seen=updated if updated != state.seen else None,
            config=config if config != state.config else None,
        )
    except StateError as error:
        log.error("%s", error)
        return 1
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    sys.exit(run(dry_run="--dry-run" in sys.argv))
