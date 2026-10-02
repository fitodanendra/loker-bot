import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from loker_bot.sources import jobstreet, kalibrr, linkedin

FIXTURES = Path(__file__).parent / "fixtures"


def load(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


class JobStreetParseTest(unittest.TestCase):
    def test_parses_jobs_with_apply_link_and_date(self):
        jobs = jobstreet.parse(json.loads(load("jobstreet.json")))

        self.assertEqual(len(jobs), 3)
        first = jobs[0]
        self.assertEqual(first.source, "JobStreet")
        self.assertTrue(first.title)
        self.assertEqual(first.url, f"https://id.jobstreet.com/id/job/{first.job_id}")
        self.assertIsNotNone(first.posted_at)
        self.assertEqual(first.posted_at.tzinfo, timezone.utc)

    def test_marks_remote_work_arrangement(self):
        raw = {"data": [{
            "id": "1", "title": "Editor", "advertiser": {"description": "PT A"},
            "locations": [{"label": "Jakarta Raya"}], "listingDate": "2026-10-01T10:00:00Z",
            "workArrangements": {"data": [{"label": {"text": "Jarak jauh"}}]},
        }]}

        jobs = jobstreet.parse(raw)

        self.assertTrue(jobs[0].is_remote)

    def test_returns_empty_list_when_data_missing(self):
        self.assertEqual(jobstreet.parse({}), [])


class KalibrrParseTest(unittest.TestCase):
    def test_parses_jobs_with_company_slug_link(self):
        jobs = kalibrr.parse(json.loads(load("kalibrr.json")))

        self.assertEqual(len(jobs), 2)
        first = jobs[0]
        self.assertEqual(first.source, "Kalibrr")
        self.assertIn("kalibrr.com/c/", first.url)
        self.assertIn(f"/jobs/{first.job_id}/", first.url)
        self.assertIn("Jakarta", first.location)
        self.assertIsNotNone(first.posted_at)


class KalibrrCountryTest(unittest.TestCase):
    def test_skips_jobs_outside_indonesia(self):
        raw = {"jobs": [{
            "id": 1, "name": "UI Designer", "slug": "ui", "company": {"code": "c"},
            "google_location": {"address_components": {"city": "Makati", "country": "Philippines"}},
        }]}

        self.assertEqual(kalibrr.parse(raw), [])


class LinkedInParseTest(unittest.TestCase):
    def test_parses_job_cards(self):
        jobs = linkedin.parse(load("linkedin.html"))

        self.assertGreater(len(jobs), 0)
        first = jobs[0]
        self.assertEqual(first.source, "LinkedIn")
        self.assertEqual(first.job_id, "4472529986")
        self.assertEqual(first.title, "Videographer & Video Editor (AI-Enabled) — Bluum")
        self.assertEqual(first.company, "Bluum")
        self.assertEqual(first.location, "Indonesia")
        self.assertEqual(first.url, "https://www.linkedin.com/jobs/view/4472529986")
        self.assertEqual(first.posted_at, datetime(2026, 10, 1, tzinfo=timezone.utc))

    def test_returns_empty_list_for_empty_html(self):
        self.assertEqual(linkedin.parse(""), [])


if __name__ == "__main__":
    unittest.main()
