import unittest

from loker_bot.commands import handle_command

CATEGORIES = ("video", "motion", "fullstack")
ALL = frozenset(CATEGORIES)


class HandleCommandTest(unittest.TestCase):
    def test_pilih_keeps_only_given_categories(self):
        active, reply = handle_command("/pilih fullstack", CATEGORIES, ALL)

        self.assertEqual(active, frozenset({"fullstack"}))
        self.assertIn("fullstack", reply)

    def test_pilih_accepts_several_categories(self):
        active, _ = handle_command("/pilih video motion", CATEGORIES, ALL)
        self.assertEqual(active, frozenset({"video", "motion"}))

    def test_tambah_adds_category(self):
        active, _ = handle_command("/tambah motion", CATEGORIES, frozenset({"video"}))
        self.assertEqual(active, frozenset({"video", "motion"}))

    def test_hapus_removes_category(self):
        active, _ = handle_command("/hapus video", CATEGORIES, ALL)
        self.assertEqual(active, frozenset({"motion", "fullstack"}))

    def test_hapus_refuses_to_remove_last_category(self):
        active, reply = handle_command("/hapus video", CATEGORIES, frozenset({"video"}))

        self.assertEqual(active, frozenset({"video"}))
        self.assertIn("minimal satu", reply.lower())

    def test_semua_activates_all(self):
        active, _ = handle_command("/semua", CATEGORIES, frozenset({"video"}))
        self.assertEqual(active, ALL)

    def test_unknown_category_is_rejected_without_change(self):
        active, reply = handle_command("/pilih dokter", CATEGORIES, ALL)

        self.assertEqual(active, ALL)
        self.assertIn("dokter", reply)

    def test_is_case_insensitive_and_ignores_bot_suffix(self):
        active, _ = handle_command("/Pilih@pencarijob_bot FullStack", CATEGORIES, ALL)
        self.assertEqual(active, frozenset({"fullstack"}))

    def test_status_lists_categories_without_change(self):
        active, reply = handle_command("/kategori", CATEGORIES, frozenset({"video"}))

        self.assertEqual(active, frozenset({"video"}))
        self.assertIn("✅ video", reply)
        self.assertIn("❌ motion", reply)

    def test_non_command_text_shows_help(self):
        active, reply = handle_command("halo", CATEGORIES, ALL)

        self.assertEqual(active, ALL)
        self.assertIn("/pilih", reply)


if __name__ == "__main__":
    unittest.main()
