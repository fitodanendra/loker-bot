"""Himalayas remote jobs (international), limited to jobs open to applicants in Indonesia.

API terms: link back to the Himalayas job page and name Himalayas as the source,
which the Telegram message does (job URL + "🔎 Himalayas").
"""

from datetime import datetime, timezone
from typing import Any, Optional

from loker_bot.http import build_url, get_json
from loker_bot.models import Job
from loker_bot.money import format_salary_range

SOURCE = "Himalayas"
SEARCH_URL = "https://himalayas.app/jobs/api/search"
COUNTRY = "Indonesia"
JOB_PATH_PREFIX = "/companies/"
MAX_LISTED_COUNTRIES = 3
PERIODS = {"hourly": "jam", "daily": "hari", "weekly": "minggu", "monthly": "bulan", "annual": "tahun"}


def search(query: str) -> list[Job]:
    url = build_url(SEARCH_URL, {"q": query, "country": COUNTRY, "sort": "recent"})
    return parse(get_json(url))


def parse(raw: dict[str, Any]) -> list[Job]:
    return [_to_job(item) for item in raw.get("jobs") or [] if _open_to_indonesia(item)]


def _open_to_indonesia(item: dict[str, Any]) -> bool:
    countries = item.get("locationRestrictions") or []
    return not countries or COUNTRY in countries


def _to_job(item: dict[str, Any]) -> Job:
    url = item.get("guid") or item.get("applicationLink") or ""
    return Job(
        source=SOURCE,
        job_id=url.split(JOB_PATH_PREFIX, 1)[-1],
        title=(item.get("title") or "").strip(),
        company=item.get("companyName") or "",
        location=_describe_countries(item.get("locationRestrictions") or []),
        url=url,
        posted_at=_from_timestamp(item.get("pubDate")),
        is_remote=True,
        salary=_salary(item),
    )


def _describe_countries(countries: list[str]) -> str:
    if not countries:
        return "Seluruh dunia"
    if len(countries) <= MAX_LISTED_COUNTRIES:
        return ", ".join(countries)
    return f"{len(countries)} negara, termasuk {COUNTRY}"


def _salary(item: dict[str, Any]) -> Optional[str]:
    if not item.get("currency"):
        return None
    return format_salary_range(
        item.get("minSalary"), item.get("maxSalary"),
        currency=item["currency"], period=PERIODS.get(item.get("salaryPeriod") or ""),
    )


def _from_timestamp(value: Any) -> Optional[datetime]:
    try:
        return datetime.fromtimestamp(int(value), timezone.utc)
    except (TypeError, ValueError):
        return None
