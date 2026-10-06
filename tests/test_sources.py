import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from loker_bot.money import format_salary_range
from loker_bot.sources import dealls, himalayas, jobstreet, kalibrr, kitalulus, linkedin

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


class DeallsParseTest(unittest.TestCase):
    def test_parses_jobs_with_slug_link_and_salary(self):
        jobs = dealls.parse(json.loads(load("dealls.json")))

        self.assertEqual(len(jobs), 3)
        first = jobs[0]
        self.assertEqual(first.source, "Dealls")
        self.assertEqual(first.job_id, "6ac3ba48a38e540012e98374")
        self.assertEqual(first.title, "Video Editor (Day Shift)")
        self.assertEqual(first.company, "Ku Creatives Unlimited")
        self.assertEqual(first.location, "Jakarta Selatan")
        self.assertEqual(
            first.url, "https://dealls.com/loker/video-editor-day-shift-2~ku-creatives-unlimited"
        )
        self.assertEqual(first.posted_at.tzinfo, timezone.utc)
        self.assertEqual(first.salary, "Rp 8.000.000 – 10.000.000")
        self.assertFalse(first.is_remote)

    def test_marks_remote_workplace(self):
        raw = {"data": {"docs": [_dealls_item(workplaceType="remote")]}}

        self.assertTrue(dealls.parse(raw)[0].is_remote)

    def test_skips_inactive_jobs_and_jobs_outside_indonesia(self):
        raw = {"data": {"docs": [
            _dealls_item(status="closed"),
            _dealls_item(country={"name": "Singapore"}),
        ]}}

        self.assertEqual(dealls.parse(raw), [])

    def test_returns_empty_list_when_docs_missing(self):
        self.assertEqual(dealls.parse({}), [])


def _dealls_item(**overrides):
    item = {
        "id": "1", "slug": "editor", "role": "Editor", "status": "active",
        "publishedAt": "2026-10-01T10:00:00Z", "workplaceType": "onSite",
        "salaryRange": None, "city": {"name": "Jakarta"}, "country": {"name": "Indonesia"},
        "company": {"name": "PT A", "slug": "pt-a"},
    }
    return {**item, **overrides}


class KitalulusParseTest(unittest.TestCase):
    NOW = datetime(2026, 10, 6, 8, 0, tzinfo=timezone.utc)  # 15:00 WIB

    def test_parses_jobs_from_embedded_page_data(self):
        jobs = kitalulus.parse(load("kitalulus.html"), self.NOW)

        self.assertEqual(len(jobs), 3)
        first = jobs[0]
        self.assertEqual(first.source, "Kitalulus")
        self.assertEqual(first.job_id, "ojxx8DGGnb5")
        self.assertEqual(first.title, "Full Stack Developer")
        self.assertEqual(first.company, "PT Istidata Indopacific Solution Centre")
        self.assertEqual(first.location, "Jakarta Utara")
        self.assertEqual(
            first.url, "https://www.kitalulus.com/lowongan/detail/full-stack-developer-j5gy"
        )
        self.assertEqual(first.salary, "Rp 6.000.000 – 9.000.000")
        self.assertEqual(first.posted_at, datetime(2026, 10, 6, tzinfo=timezone.utc))
        self.assertIsNone(jobs[1].salary)

    def test_returns_empty_list_when_page_has_no_vacancies(self):
        self.assertEqual(kitalulus.parse("<html></html>", self.NOW), [])

    def test_skips_closed_jobs(self):
        html = load("kitalulus.html").replace('isClosed\\": false', 'isClosed\\": true', 1)

        self.assertEqual(len(kitalulus.parse(html, self.NOW)), 2)


class KitalulusDateTest(unittest.TestCase):
    NOW = datetime(2026, 10, 6, 20, 0, tzinfo=timezone.utc)  # already 7 Oct in WIB

    def test_parses_relative_and_absolute_dates_as_wib_calendar_days(self):
        cases = {
            "Terakhir diperbarui hari ini": datetime(2026, 10, 7, tzinfo=timezone.utc),
            "Terakhir diperbarui 1 hari yang lalu": datetime(2026, 10, 6, tzinfo=timezone.utc),
            "Terakhir diperbarui 2 minggu yang lalu": datetime(2026, 9, 23, tzinfo=timezone.utc),
            "Terakhir diperbarui pada 26 Sep 2026": datetime(2026, 9, 26, tzinfo=timezone.utc),
            "Terakhir diperbarui pada 3 Agu 2026": datetime(2026, 8, 3, tzinfo=timezone.utc),
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(kitalulus.parse_updated(text, self.NOW), expected)

    def test_returns_none_for_unknown_format(self):
        self.assertIsNone(kitalulus.parse_updated("Baru saja", self.NOW))


class HimalayasParseTest(unittest.TestCase):
    def test_parses_remote_jobs_with_link_back_and_salary(self):
        jobs = himalayas.parse(json.loads(load("himalayas.json")))

        self.assertEqual(len(jobs), 3)
        first = jobs[0]
        self.assertEqual(first.source, "Himalayas")
        self.assertEqual(first.job_id, "g2i/jobs/senior-engineer-1499993060")
        self.assertEqual(first.title, "Senior Engineer")
        self.assertEqual(first.company, "G2i")
        self.assertEqual(first.url, "https://himalayas.app/companies/g2i/jobs/senior-engineer-1499993060")
        self.assertEqual(first.location, "Seluruh dunia")
        self.assertTrue(first.is_remote)
        self.assertEqual(first.salary, "USD 50 – 150 / jam")
        self.assertEqual(first.posted_at, datetime.fromtimestamp(1791079599, timezone.utc))
        self.assertIsNone(jobs[1].salary)

    def test_describes_country_restrictions(self):
        few = _himalayas_item(locationRestrictions=["Indonesia", "Malaysia"])
        many = _himalayas_item(locationRestrictions=["Indonesia", "Japan", "India", "Vietnam"])

        jobs = himalayas.parse({"jobs": [few, many]})

        self.assertEqual(jobs[0].location, "Indonesia, Malaysia")
        self.assertEqual(jobs[1].location, "4 negara, termasuk Indonesia")

    def test_skips_jobs_not_open_to_indonesia(self):
        raw = {"jobs": [_himalayas_item(locationRestrictions=["United States"])]}

        self.assertEqual(himalayas.parse(raw), [])

    def test_returns_empty_list_when_jobs_missing(self):
        self.assertEqual(himalayas.parse({}), [])


def _himalayas_item(**overrides):
    item = {
        "title": "Video Editor", "companyName": "Acme", "minSalary": 60000, "maxSalary": 90000,
        "salaryPeriod": "annual", "currency": "USD", "locationRestrictions": [],
        "pubDate": 1791079599, "guid": "https://himalayas.app/companies/acme/jobs/video-editor",
    }
    return {**item, **overrides}


class MoneyTest(unittest.TestCase):
    def test_formats_rupiah_and_foreign_ranges(self):
        self.assertEqual(format_salary_range(8_000_000, 10_000_000), "Rp 8.000.000 – 10.000.000")
        self.assertEqual(format_salary_range(5_000_000, None), "Rp 5.000.000")
        self.assertEqual(
            format_salary_range(60000, 90000, currency="USD", period="tahun"),
            "USD 60.000 – 90.000 / tahun",
        )
        self.assertIsNone(format_salary_range(0, 0))


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
