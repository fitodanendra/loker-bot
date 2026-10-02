from typing import Any

from loker_bot.dates import parse_iso
from loker_bot.http import build_url, get_json
from loker_bot.models import Job

SOURCE = "JobStreet"
SEARCH_URL = "https://id.jobstreet.com/api/jobsearch/v5/search"
JOB_URL = "https://id.jobstreet.com/id/job/{job_id}"
PAGE_SIZE = 30
REMOTE_LABELS = {"jarak jauh", "remote"}


def search(query: str) -> list[Job]:
    url = build_url(SEARCH_URL, {
        "siteKey": "ID-Main",
        "sourcesystem": "houston",
        "page": 1,
        "pageSize": PAGE_SIZE,
        "keywords": query,
        "sortmode": "ListedDate",
        "locale": "id-ID",
    })
    return parse(get_json(url))


def parse(raw: dict[str, Any]) -> list[Job]:
    return [_to_job(item) for item in raw.get("data") or []]


def _to_job(item: dict[str, Any]) -> Job:
    job_id = str(item["id"])
    locations = item.get("locations") or [{}]
    arrangements = (item.get("workArrangements") or {}).get("data") or []
    arrangement_labels = {
        (a.get("label") or {}).get("text", "").lower() for a in arrangements
    }
    return Job(
        source=SOURCE,
        job_id=job_id,
        title=item.get("title", "").strip(),
        company=(item.get("advertiser") or {}).get("description", "").strip(),
        location=locations[0].get("label", ""),
        url=JOB_URL.format(job_id=job_id),
        posted_at=parse_iso(item.get("listingDate")),
        is_remote=bool(arrangement_labels & REMOTE_LABELS),
        salary=item.get("salaryLabel") or None,
    )
