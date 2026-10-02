from typing import Any

from loker_bot.dates import parse_iso
from loker_bot.http import build_url, get_json
from loker_bot.models import Job

SOURCE = "Kalibrr"
SEARCH_URL = "https://www.kalibrr.com/kjs/job_board/search"
JOB_URL = "https://www.kalibrr.com/c/{company}/jobs/{job_id}/{slug}"
PAGE_SIZE = 30
COUNTRY = "indonesia"


def search(query: str) -> list[Job]:
    url = build_url(SEARCH_URL, {"limit": PAGE_SIZE, "offset": 0, "text": query})
    return parse(get_json(url))


def parse(raw: dict[str, Any]) -> list[Job]:
    return [_to_job(item) for item in raw.get("jobs") or [] if _in_indonesia(item)]


def _in_indonesia(item: dict[str, Any]) -> bool:
    address = ((item.get("google_location") or {}).get("address_components")) or {}
    country = (address.get("country") or COUNTRY).lower()
    return country == COUNTRY


def _to_job(item: dict[str, Any]) -> Job:
    job_id = str(item["id"])
    company = item.get("company") or {}
    address = ((item.get("google_location") or {}).get("address_components")) or {}
    location = ", ".join(
        part for part in (address.get("city"), address.get("region")) if part
    )
    return Job(
        source=SOURCE,
        job_id=job_id,
        title=item.get("name", "").strip(),
        company=item.get("company_name") or company.get("name", ""),
        location=location,
        url=JOB_URL.format(
            company=company.get("code", ""), job_id=job_id, slug=item.get("slug", "")
        ),
        posted_at=parse_iso(item.get("activation_date")),
        is_remote=bool(item.get("is_work_from_home")),
    )
