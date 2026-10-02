import unittest

from loker_bot.custom import MAX_CUSTOM, custom_searches, handle_custom_command

BUILTIN = ("video", "motion")
ACTIVE = frozenset(BUILTIN)


class BaruTest(unittest.TestCase):
    def test_creates_and_activates_new_category(self):
        custom, active, reply = handle_custom_command(
            "/baru Graphic Designer", BUILTIN, {}, ACTIVE)

        self.assertEqual(custom, {"graphicdesigner": "graphic designer"})
        self.assertIn("graphicdesigner", active)
        self.assertIn("graphic designer", reply)

    def test_does_not_mutate_inputs(self):
        original = {"a": "a"}
        handle_custom_command("/baru b", BUILTIN, original, ACTIVE)
        self.assertEqual(original, {"a": "a"})

    def test_rejects_empty_keyword(self):
        custom, active, reply = handle_custom_command("/baru", BUILTIN, {}, ACTIVE)

        self.assertEqual(custom, {})
        self.assertIn("/baru graphic designer", reply)

    def test_rejects_duplicate_of_builtin_or_existing(self):
        custom, _, reply = handle_custom_command("/baru Video", BUILTIN, {}, ACTIVE)

        self.assertEqual(custom, {})
        self.assertIn("sudah ada", reply)

    def test_rejects_when_limit_reached(self):
        full = {f"k{i}": f"k{i}" for i in range(MAX_CUSTOM)}

        custom, _, reply = handle_custom_command("/baru extra", BUILTIN, full, ACTIVE)

        self.assertEqual(custom, full)
        self.assertIn(str(MAX_CUSTOM), reply)

    def test_rejects_too_long_keyword(self):
        custom, _, _ = handle_custom_command("/baru " + "a" * 61, BUILTIN, {}, ACTIVE)
        self.assertEqual(custom, {})


class BuangTest(unittest.TestCase):
    def test_removes_custom_category_by_name_or_keyword(self):
        custom = {"graphicdesigner": "graphic designer"}
        active = ACTIVE | {"graphicdesigner"}

        new_custom, new_active, _ = handle_custom_command(
            "/buang graphic designer", BUILTIN, custom, active)

        self.assertEqual(new_custom, {})
        self.assertEqual(new_active, ACTIVE)

    def test_refuses_to_remove_builtin(self):
        custom, active, reply = handle_custom_command("/buang video", BUILTIN, {}, ACTIVE)

        self.assertEqual(active, ACTIVE)
        self.assertIn("/hapus", reply)

    def test_reactivates_everything_when_last_active_removed(self):
        custom = {"x": "x"}

        _, active, _ = handle_custom_command("/buang x", BUILTIN, custom, frozenset({"x"}))

        self.assertEqual(active, ACTIVE)


class OtherCommandsTest(unittest.TestCase):
    def test_returns_none_for_non_custom_commands(self):
        self.assertIsNone(handle_custom_command("/pilih video", BUILTIN, {}, ACTIVE))


class CustomSearchesTest(unittest.TestCase):
    def test_builds_search_requiring_all_words(self):
        searches = custom_searches({"graphicdesigner": "graphic designer"})

        self.assertEqual(searches[0].name, "graphicdesigner")
        self.assertEqual(searches[0].query, "graphic designer")
        self.assertEqual(searches[0].title_must_include_all, ("graphic", "designer"))


if __name__ == "__main__":
    unittest.main()
