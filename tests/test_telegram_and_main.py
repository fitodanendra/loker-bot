import unittest
from datetime import datetime, timedelta, timezone

from loker_bot.main import collect_new_jobs, notify
from loker_bot.models import Job, Search, Settings
from loker_bot.telegram import format_message

NOW = datetime(2026, 10, 2, 5, 0, tzinfo=timezone.utc)
SETTINGS = Settings(locations=("Jakarta",), include_remote=True, max_age_hours=48)


def make_job(job_id="1", **overrides):
    base = dict(
        source="JobStreet", job_id=job_id, title="Video Editor", company="PT <A>",
        location="Jakarta Raya", url=f"https://x/{job_id}", posted_at=NOW,
        is_remote=False, salary="Rp 5.000.000",
    )
    return Job(**{**base, **overrides})


class FormatMessageTest(unittest.TestCase):
    def test_escapes_html_and_shows_wib_time(self):
        text = format_message(make_job(), "video editor")

        self.assertIn("<b>Video Editor</b>", text)
        self.assertIn("PT &lt;A&gt;", text)
        self.assertIn("12:00 WIB", text)
        self.assertIn("Rp 5.000.000", text)
        self.assertIn("JobStreet", text)

    def test_shows_date_only_when_source_has_no_time(self):
        job = make_job(posted_at=datetime(2026, 10, 1, tzinfo=timezone.utc))

        text = format_message(job, "video editor")

        self.assertIn("01 Oct 2026", text)
        self.assertNotIn("WIB", text)

    def test_marks_remote_jobs(self):
        text = format_message(make_job(is_remote=True), "video editor")
        self.assertIn("Remote", text)


class CollectNewJobsTest(unittest.TestCase):
    def test_skips_seen_failing_and_unwanted_jobs_and_dedupes(self):
        searches = [Search("video editor", ("video",)), Search("videographer", ("video",))]

        def good_source(query):
            return [make_job("1"), make_job("2"), make_job("3", title="Content Creator")]

        def broken_source(query):
            raise OSError("network down")

        jobs = collect_new_jobs(
            searches, SETTINGS, seen={"JobStreet:2": NOW.isoformat()},
            sources={"good": good_source, "broken": broken_source}, now=NOW,
        )

        self.assertEqual([job.uid for job, _ in jobs], ["JobStreet:1"])

    def test_orders_oldest_first(self):
        older = make_job("old", posted_at=NOW - timedelta(hours=3))
        newer = make_job("new", posted_at=NOW)

        jobs = collect_new_jobs(
            [Search("video")], SETTINGS, seen={},
            sources={"s": lambda q: [newer, older]}, now=NOW,
        )

        self.assertEqual([job.job_id for job, _ in jobs], ["old", "new"])


class NotifyTest(unittest.TestCase):
    def test_marks_only_successfully_sent_jobs_as_seen(self):
        jobs = [(make_job("1"), "q"), (make_job("2"), "q")]
        sent = []

        def send(job, query):
            if job.job_id == "2":
                raise OSError("telegram down")
            sent.append(job.uid)

        seen = notify(jobs, {}, send, NOW, max_per_run=10)

        self.assertEqual(sent, ["JobStreet:1"])
        self.assertEqual(set(seen), {"JobStreet:1"})

    def test_respects_max_per_run(self):
        jobs = [(make_job(str(i)), "q") for i in range(5)]

        seen = notify(jobs, {}, lambda job, query: None, NOW, max_per_run=2)

        self.assertEqual(len(seen), 2)


if __name__ == "__main__":
    unittest.main()
