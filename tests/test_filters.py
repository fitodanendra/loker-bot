import unittest
from datetime import datetime, timedelta, timezone

from loker_bot.filters import is_wanted
from loker_bot.models import Job, Search, Settings

NOW = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)


def make_job(**overrides):
    base = dict(
        source="JobStreet", job_id="1", title="Video Editor", company="PT A",
        location="Jakarta Selatan, Jakarta Raya", url="https://x", posted_at=NOW,
        is_remote=False, salary=None,
    )
    return Job(**{**base, **overrides})


SETTINGS = Settings(locations=("Jakarta",), include_remote=True, max_age_hours=48)
SEARCH = Search(query="video editor", title_must_include=("video", "editor"))


class IsWantedTest(unittest.TestCase):
    def test_accepts_matching_job_in_location(self):
        self.assertTrue(is_wanted(make_job(), SEARCH, SETTINGS, NOW))

    def test_rejects_title_without_required_words(self):
        job = make_job(title="Content Creator")
        self.assertFalse(is_wanted(job, SEARCH, SETTINGS, NOW))

    def test_title_match_is_case_insensitive(self):
        job = make_job(title="VIDEOGRAPHER")
        self.assertTrue(is_wanted(job, SEARCH, SETTINGS, NOW))

    def test_accepts_any_title_when_no_title_filter(self):
        job = make_job(title="Content Creator")
        self.assertTrue(is_wanted(job, Search(query="video editor"), SETTINGS, NOW))

    def test_rejects_other_location(self):
        job = make_job(location="Surabaya, Jawa Timur")
        self.assertFalse(is_wanted(job, SEARCH, SETTINGS, NOW))

    def test_accepts_remote_job_from_other_location(self):
        job = make_job(location="Surabaya, Jawa Timur", is_remote=True)
        self.assertTrue(is_wanted(job, SEARCH, SETTINGS, NOW))

    def test_rejects_remote_job_when_remote_disabled(self):
        settings = Settings(locations=("Jakarta",), include_remote=False, max_age_hours=48)
        job = make_job(location="Surabaya", is_remote=True)
        self.assertFalse(is_wanted(job, SEARCH, settings, NOW))

    def test_accepts_everywhere_when_no_locations(self):
        settings = Settings(locations=(), include_remote=True, max_age_hours=48)
        job = make_job(location="Surabaya")
        self.assertTrue(is_wanted(job, SEARCH, settings, NOW))

    def test_rejects_job_older_than_max_age(self):
        job = make_job(posted_at=NOW - timedelta(hours=49))
        self.assertFalse(is_wanted(job, SEARCH, SETTINGS, NOW))

    def test_accepts_job_without_date(self):
        job = make_job(posted_at=None)
        self.assertTrue(is_wanted(job, SEARCH, SETTINGS, NOW))


if __name__ == "__main__":
    unittest.main()
