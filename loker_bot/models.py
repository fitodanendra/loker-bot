from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class Job:
    source: str
    job_id: str
    title: str
    company: str
    location: str
    url: str
    posted_at: Optional[datetime]
    is_remote: bool = False
    salary: Optional[str] = None

    @property
    def uid(self) -> str:
        return f"{self.source}:{self.job_id}"


@dataclass(frozen=True)
class Search:
    query: str
    title_must_include: tuple[str, ...] = ()
    name: str = ""
    title_must_include_all: tuple[str, ...] = ()


@dataclass(frozen=True)
class Settings:
    locations: tuple[str, ...]
    include_remote: bool
    max_age_hours: int
