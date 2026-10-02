import tempfile
import unittest
from pathlib import Path

from loker_bot.inbox import Prefs, active_searches, load_prefs, process_updates, save_prefs
from loker_bot.models import Search

CATEGORIES = ("video", "motion", "fullstack")
OWNER = "100"


def update(update_id, text, chat_id=100):
    return {"update_id": update_id, "message": {"chat": {"id": chat_id}, "text": text}}


class ProcessUpdatesTest(unittest.TestCase):
    def test_applies_owner_commands_in_order_and_tracks_last_id(self):
        prefs = Prefs(active=frozenset(CATEGORIES), last_update_id=0)
        updates = [update(5, "/pilih video"), update(6, "/tambah motion")]

        new_prefs, replies = process_updates(updates, OWNER, CATEGORIES, prefs)

        self.assertEqual(new_prefs.active, frozenset({"video", "motion"}))
        self.assertEqual(new_prefs.last_update_id, 6)
        self.assertEqual(len(replies), 2)

    def test_ignores_messages_from_other_chats(self):
        prefs = Prefs(active=frozenset(CATEGORIES), last_update_id=0)

        new_prefs, replies = process_updates(
            [update(7, "/pilih video", chat_id=999)], OWNER, CATEGORIES, prefs,
        )

        self.assertEqual(new_prefs.active, frozenset(CATEGORIES))
        self.assertEqual(new_prefs.last_update_id, 7)
        self.assertEqual(replies, [])

    def test_ignores_updates_without_text(self):
        prefs = Prefs(active=frozenset(CATEGORIES), last_update_id=0)
        updates = [{"update_id": 8, "message": {"chat": {"id": 100}, "sticker": {}}}]

        new_prefs, replies = process_updates(updates, OWNER, CATEGORIES, prefs)

        self.assertEqual(replies, [])
        self.assertEqual(new_prefs.last_update_id, 8)


class ActiveSearchesTest(unittest.TestCase):
    def test_returns_only_active_searches(self):
        searches = [Search("video editor", name="video"), Search("motion", name="motion")]

        result = active_searches(searches, frozenset({"motion"}))

        self.assertEqual([s.name for s in result], ["motion"])

    def test_falls_back_to_all_when_nothing_matches(self):
        searches = [Search("video editor", name="video")]
        self.assertEqual(active_searches(searches, frozenset({"removed"})), searches)


class PrefsStorageTest(unittest.TestCase):
    def test_missing_file_activates_all_categories(self):
        prefs = load_prefs(Path("/nonexistent/prefs.json"), CATEGORIES)

        self.assertEqual(prefs, Prefs(active=frozenset(CATEGORIES), last_update_id=0))

    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prefs.json"
            prefs = Prefs(active=frozenset({"video"}), last_update_id=42)

            save_prefs(path, prefs)

            self.assertEqual(load_prefs(path, CATEGORIES), prefs)


if __name__ == "__main__":
    unittest.main()
