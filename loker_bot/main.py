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
from typing import Callable

from loker_bot.config import ConfigError, load_config
from loker_bot.custom import custom_searches
from loker_bot.filters import is_wanted
from loker_bot.inbox import Prefs, active_searches, load_prefs, process_updates, save_prefs
from loker_bot.models import Job, Search, Settings
from loker_bot.sources import jobstreet, kalibrr, linkedin
from loker_bot.store import Seen, load_seen, prune_seen, save_seen, with_seen
from loker_bot.telegram import TelegramClient, format_message

log = logging.getLogger("loker_bot")

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"
SEEN_PATH = ROOT / "seen.json"
PREFS_PATH = ROOT / "prefs.json"
MAX_PER_RUN = 25
KEEP_SEEN_DAYS = 30
SECONDS_BETWEEN_MESSAGES = 1.1
BOT_COMMANDS = [
    ("kategori", "Lihat kategori aktif"),
    ("pilih", "Hanya kategori ini, mis. /pilih fullstack"),
    ("tambah", "Aktifkan kategori, mis. /tambah motion"),
    ("hapus", "Matikan kategori, mis. /hapus video"),
    ("semua", "Aktifkan semua kategori"),
    ("baru", "Buat kategori baru, mis. /baru graphic designer"),
    ("buang", "Hapus kategori buatan sendiri"),
    ("lokasi", "Lihat lokasi aktif"),
    ("tambahlokasi", "Tambah lokasi, mis. /tambahlokasi bandung"),
    ("hapuslokasi", "Hapus lokasi, mis. /hapuslokasi bogor"),
    ("semualokasi", "Cari di seluruh Indonesia"),
]

SourceFn = Callable[[str], list[Job]]
SendFn = Callable[[Job, str], None]

SOURCES: dict[str, SourceFn] = {
    "JobStreet": jobstreet.search,
    "Kalibrr": kalibrr.search,
    "LinkedIn": linkedin.search,
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


def _read_commands(
    client: TelegramClient, categories: tuple[str, ...], default_locations: tuple[str, ...],
) -> Prefs:
    """Apply category commands the owner sent since the last run, and answer them."""
    prefs = load_prefs(PREFS_PATH, categories)
    try:
        client.set_commands(BOT_COMMANDS)
        updates = client.get_updates(prefs.last_update_id)
    except Exception as error:
        log.warning("Could not read Telegram commands: %s", error)
        return prefs

    new_prefs, replies = process_updates(
        updates, client.chat_id, categories, prefs, default_locations,
    )
    for reply in replies:
        try:
            client.send_text(reply)
        except Exception as error:
            log.warning("Could not answer command: %s", error)
    save_prefs(PREFS_PATH, new_prefs)
    return new_prefs


def run(dry_run: bool) -> int:
    now = datetime.now(timezone.utc)
    try:
        searches, settings = load_config(CONFIG_PATH)
        client = None if dry_run else _telegram_client()
    except ConfigError as error:
        log.error("%s", error)
        return 1

    categories = tuple(search.name for search in searches)
    if client is None:
        prefs = load_prefs(PREFS_PATH, categories)
        send = _print_sender
    else:
        prefs = _read_commands(client, categories, settings.locations)
        send = _telegram_sender(client)
    if prefs.locations is not None:
        settings = replace(settings, locations=prefs.locations)
    chosen = active_searches(searches + custom_searches(prefs.custom), prefs.active)
    log.info("Active categories: %s", ", ".join(search.name for search in chosen))
    log.info("Locations: %s", ", ".join(settings.locations) or "all of Indonesia")

    seen = prune_seen(load_seen(SEEN_PATH), now, KEEP_SEEN_DAYS)
    jobs = collect_new_jobs(chosen, settings, seen, SOURCES, now)
    log.info("Found %d new matching jobs", len(jobs))

    updated = notify(jobs, seen, send, now, MAX_PER_RUN)
    if not dry_run:
        save_seen(SEEN_PATH, updated)
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    sys.exit(run(dry_run="--dry-run" in sys.argv))
