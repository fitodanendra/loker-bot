import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from loker_bot.config import ConfigError, load_config
from loker_bot.store import prune_seen, with_seen

NOW = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)


class StoreTest(unittest.TestCase):
    def test_with_seen_does_not_mutate_original(self):
        original = {"a": NOW.isoformat()}

        updated = with_seen(original, ["b"], NOW)

        self.assertEqual(original, {"a": NOW.isoformat()})
        self.assertEqual(set(updated), {"a", "b"})

    def test_prune_removes_old_entries(self):
        seen = {"old": (NOW - timedelta(days=31)).isoformat(), "new": NOW.isoformat()}

        self.assertEqual(set(prune_seen(seen, NOW, keep_days=30)), {"new"})


class ConfigTest(unittest.TestCase):
    def write(self, tmp, data):
        path = Path(tmp) / "config.json"
        path.write_text(json.dumps(data))
        return path

    def test_loads_valid_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, {
                "searches": [{"query": "video editor", "title_must_include": ["video"]}],
                "locations": ["Jakarta"], "include_remote": True, "max_age_hours": 48,
            })

            searches, settings = load_config(path)

            self.assertEqual(searches[0].query, "video editor")
            self.assertEqual(searches[0].title_must_include, ("video",))
            self.assertEqual(settings.locations, ("Jakarta",))

    def test_rejects_empty_searches(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, {"searches": []})
            with self.assertRaises(ConfigError):
                load_config(path)

    def test_rejects_search_without_query(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, {"searches": [{"title_must_include": ["x"]}]})
            with self.assertRaises(ConfigError):
                load_config(path)


if __name__ == "__main__":
    unittest.main()
