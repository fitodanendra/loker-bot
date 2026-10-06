"""Kitalulus search page. Its own API ranks poorly, so we read the data the website embeds."""

import json
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from loker_bot.http import build_url, get_text
from loker_bot.models import Job
from loker_bot.money import format_salary_range

SOURCE = "Kitalulus"
SEARCH_URL = "https://www.kitalulus.com/lowongan"
JOB_URL = "https://www.kitalulus.com/lowongan/detail/{slug}"
VACANCY_LIST_KEY = '"vacancyList":'
WIB = timezone(timedelta(hours=7))

# Next.js streams page data as JSON strings inside self.__next_f.push([1, "..."]) calls.
NEXT_DATA_CHUNK = re.compile(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)')

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "mei": 5, "may": 5, "jun": 6, "jul": 7,
    "agu": 8, "agt": 8, "aug": 8, "sep": 9, "okt": 10, "oct": 10, "nov": 11, "des": 12, "dec": 12,
}
TODAY = re.compile(r"hari ini")
DAYS_AGO = re.compile(r"(\d+) hari yang lalu")
WEEKS_AGO = re.compile(r"(\d+) minggu yang lalu")
ON_DATE = re.compile(r"pada (\d{1,2}) ([a-z]{3})[a-z]* (\d{4})")


def search(query: str) -> list[Job]:
    url = build_url(SEARCH_URL, {"keyword": query, "sortBy": "updatedAt"})
    return parse(get_text(url), datetime.now(timezone.utc))


def parse(html: str, now: datetime) -> list[Job]:
    jobs = []
    for item in _vacancies(html):
        posted_at = parse_updated(item.get("updatedAtStr") or "", now)
        if item.get("isClosed") or posted_at is None:
            continue  # without a date we cannot tell old jobs from new ones
        jobs.append(_to_job(item, posted_at))
    return jobs


def parse_updated(text: str, now: datetime) -> Optional[datetime]:
    """Turn 'Terakhir diperbarui 1 hari yang lalu' etc. into that WIB day, as midnight UTC.

    Midnight marks a date-only value, so Telegram shows the day without a made-up time.
    """
    today = now.astimezone(WIB).date()
    text = text.lower()
    if TODAY.search(text):
        return _as_utc_day(today)
    if match := DAYS_AGO.search(text):
        return _as_utc_day(today - timedelta(days=int(match.group(1))))
    if match := WEEKS_AGO.search(text):
        return _as_utc_day(today - timedelta(weeks=int(match.group(1))))
    if (match := ON_DATE.search(text)) and match.group(2) in MONTHS:
        day, month, year = int(match.group(1)), MONTHS[match.group(2)], int(match.group(3))
        return _as_utc_day(date(year, month, day))
    return None


def _as_utc_day(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=timezone.utc)


def _vacancies(html: str) -> list[dict[str, Any]]:
    payload = "".join(json.loads(chunk) for chunk in NEXT_DATA_CHUNK.findall(html))
    start = payload.find(VACANCY_LIST_KEY)
    if start < 0:
        return []
    vacancy_list, _ = json.JSONDecoder().raw_decode(payload, start + len(VACANCY_LIST_KEY))
    return (vacancy_list or {}).get("list") or []


def _to_job(item: dict[str, Any], posted_at: datetime) -> Job:
    return Job(
        source=SOURCE,
        job_id=str(item["id"]),
        title=(item.get("positionName") or "").strip(),
        company=(item.get("company") or {}).get("name", ""),
        location=(item.get("city") or {}).get("name", ""),
        url=JOB_URL.format(slug=item.get("slug", "")),
        posted_at=posted_at,
        salary=format_salary_range(item.get("salaryLowerBound"), item.get("salaryUpperBound")),
    )
