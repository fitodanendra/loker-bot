import html
import re

from loker_bot.dates import parse_iso
from loker_bot.http import build_url, get_text
from loker_bot.models import Job

SOURCE = "LinkedIn"
SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
JOB_URL = "https://www.linkedin.com/jobs/view/{job_id}"
PAST_24_HOURS = "r86400"
SORT_BY_DATE = "DD"

_CARD = re.compile(r"<li>(.*?)</li>", re.S)
_ID = re.compile(r'urn:li:jobPosting:(\d+)')
_TITLE = re.compile(r'class="base-search-card__title">(.*?)</h3>', re.S)
_COMPANY = re.compile(r'class="base-search-card__subtitle">(.*?)</h4>', re.S)
_LOCATION = re.compile(r'class="job-search-card__location">(.*?)</span>', re.S)
_DATE = re.compile(r'<time[^>]*datetime="([^"]+)"')
_TAGS = re.compile(r"<[^>]+>")


def search(query: str, location: str = "Indonesia") -> list[Job]:
    url = build_url(SEARCH_URL, {
        "keywords": query,
        "location": location,
        "f_TPR": PAST_24_HOURS,
        "sortBy": SORT_BY_DATE,
        "start": 0,
    })
    return parse(get_text(url))


def parse(page: str) -> list[Job]:
    jobs = (_to_job(card) for card in _CARD.findall(page))
    return [job for job in jobs if job is not None]


def _to_job(card: str):
    job_id = _ID.search(card)
    title = _TITLE.search(card)
    if not job_id or not title:
        return None
    date = _DATE.search(card)
    return Job(
        source=SOURCE,
        job_id=job_id.group(1),
        title=_clean(title.group(1)),
        company=_clean_match(_COMPANY.search(card)),
        location=_clean_match(_LOCATION.search(card)),
        url=JOB_URL.format(job_id=job_id.group(1)),
        posted_at=parse_iso(date.group(1)) if date else None,
    )


def _clean_match(match) -> str:
    return _clean(match.group(1)) if match else ""


def _clean(fragment: str) -> str:
    return " ".join(html.unescape(_TAGS.sub("", fragment)).split())
