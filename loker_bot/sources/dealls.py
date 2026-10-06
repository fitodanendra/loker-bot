from typing import Any, Optional

from loker_bot.dates import parse_iso
from loker_bot.http import build_url, get_json
from loker_bot.models import Job

SOURCE = "Dealls"
SEARCH_URL = "https://api.sejutacita.id/v1/explore-job/job"
JOB_URL = "https://dealls.com/loker/{slug}~{company}"
PAGE_SIZE = 30
COUNTRY = "indonesia"
ACTIVE = "active"
REMOTE = "remote"


def search(query: str) -> list[Job]:
    url = build_url(SEARCH_URL, {
        "page": 1,
        "limit": PAGE_SIZE,
        "search": query,
        "sortParam": "publishedAt",
        "sortBy": "desc",
    })
    return parse(get_json(url))


def parse(raw: dict[str, Any]) -> list[Job]:
    docs = (raw.get("data") or {}).get("docs") or []
    return [_to_job(item) for item in docs if _is_open_in_indonesia(item)]


def _is_open_in_indonesia(item: dict[str, Any]) -> bool:
    country = ((item.get("country") or {}).get("name") or COUNTRY).lower()
    return (item.get("status") or ACTIVE) == ACTIVE and country == COUNTRY


def _to_job(item: dict[str, Any]) -> Job:
    company = item.get("company") or {}
    return Job(
        source=SOURCE,
        job_id=str(item["id"]),
        title=(item.get("role") or "").strip(),
        company=company.get("name", ""),
        location=(item.get("city") or {}).get("name", ""),
        url=JOB_URL.format(slug=item.get("slug", ""), company=company.get("slug", "")),
        posted_at=parse_iso(item.get("publishedAt")),
        is_remote=item.get("workplaceType") == REMOTE,
        salary=_format_salary(item.get("salaryRange")),
    )


def _format_salary(salary_range: Optional[dict[str, Any]]) -> Optional[str]:
    if not salary_range or not salary_range.get("start"):
        return None
    start, end = salary_range["start"], salary_range.get("end")
    if not end or end == start:
        return f"Rp {_rupiah(start)}"
    return f"Rp {_rupiah(start)} – {_rupiah(end)}"


def _rupiah(amount: int) -> str:
    return f"{amount:,}".replace(",", ".")
