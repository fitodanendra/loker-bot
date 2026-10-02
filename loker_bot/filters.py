from datetime import datetime, timedelta

from loker_bot.models import Job, Search, Settings


def is_wanted(job: Job, search: Search, settings: Settings, now: datetime) -> bool:
    return (
        _title_matches(job, search)
        and _location_matches(job, settings)
        and _is_recent(job, settings, now)
    )


def _title_matches(job: Job, search: Search) -> bool:
    if not search.title_must_include:
        return True
    title = job.title.lower()
    return any(word.lower() in title for word in search.title_must_include)


def _location_matches(job: Job, settings: Settings) -> bool:
    if not settings.locations:
        return True
    if settings.include_remote and job.is_remote:
        return True
    location = job.location.lower()
    return any(place.lower() in location for place in settings.locations)


def _is_recent(job: Job, settings: Settings, now: datetime) -> bool:
    if job.posted_at is None:
        return True
    return now - job.posted_at <= timedelta(hours=settings.max_age_hours)
