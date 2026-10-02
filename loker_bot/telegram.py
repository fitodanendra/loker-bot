import html
import json
import logging
import time
import urllib.error
from datetime import datetime, timedelta, timezone

from loker_bot.http import post_json
from loker_bot.models import Job

log = logging.getLogger(__name__)

API_URL = "https://api.telegram.org/bot{token}/{method}"
WIB = timezone(timedelta(hours=7), "WIB")
TOO_MANY_REQUESTS = 429
APPLY_BUTTON_TEXT = "📝 Lamar / Lihat Lowongan"


def format_message(job: Job, query: str) -> str:
    lines = [
        f"🆕 <b>{_e(job.title)}</b>",
        f"🏢 {_e(job.company or '-')}",
        f"📍 {_e(job.location or '-')}" + (" · 🏠 Remote" if job.is_remote else ""),
    ]
    if job.salary:
        lines.append(f"💰 {_e(job.salary)}")
    if job.posted_at:
        lines.append(f"🕒 Diposting: {_format_time(job.posted_at)}")
    lines.append(f"🔎 {_e(job.source)} · kata kunci “{_e(query)}”")
    return "\n".join(lines)


def _format_time(moment: datetime) -> str:
    is_date_only = (moment.hour, moment.minute, moment.second) == (0, 0, 0)
    if is_date_only:
        return moment.strftime("%d %b %Y")
    return moment.astimezone(WIB).strftime("%d %b %Y, %H:%M WIB")


def _e(text: str) -> str:
    return html.escape(text, quote=False)


class TelegramClient:
    def __init__(self, token: str, chat_id: str):
        self._token = token
        self._chat_id = chat_id

    @property
    def chat_id(self) -> str:
        return self._chat_id

    def send_job(self, job: Job, query: str) -> None:
        self._call("sendMessage", {
            "chat_id": self._chat_id,
            "text": format_message(job, query),
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "reply_markup": {"inline_keyboard": [[{"text": APPLY_BUTTON_TEXT, "url": job.url}]]},
        })

    def _call(self, method: str, payload: dict) -> dict:
        url = API_URL.format(token=self._token, method=method)
        try:
            return post_json(url, payload)
        except urllib.error.HTTPError as error:
            retry_after = _retry_after(error)
            if retry_after is None:
                raise RuntimeError(f"Telegram {method} failed: HTTP {error.code}") from error
            log.info("Telegram rate limit hit, waiting %ss", retry_after)
            time.sleep(retry_after)
            return post_json(url, payload)


def _retry_after(error: urllib.error.HTTPError):
    if error.code != TOO_MANY_REQUESTS:
        return None
    try:
        body = json.loads(error.read().decode("utf-8"))
        return int(body["parameters"]["retry_after"])
    except (ValueError, KeyError, TypeError):
        return 5
