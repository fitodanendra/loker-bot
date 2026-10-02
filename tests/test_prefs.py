import unittest

from loker_bot.models import Search
from loker_bot.prefs import Prefs, active_searches, custom_searches, prefs_from_dict

CATEGORIES = ("video", "motion")


class PrefsFromDictTest(unittest.TestCase):
    def test_missing_prefs_activate_all_builtin_categories(self):
        prefs = prefs_from_dict(None, CATEGORIES)

        self.assertEqual(prefs, Prefs(active=frozenset(CATEGORIES), custom={}, locations=None))

    def test_reads_custom_categories_and_locations(self):
        raw = {"active": ["video", "gd"], "custom": {"gd": "graphic designer"}, "locations": ["Bandung"]}

        prefs = prefs_from_dict(raw, CATEGORIES)

        self.assertEqual(prefs.active, frozenset({"video", "gd"}))
        self.assertEqual(prefs.custom, {"gd": "graphic designer"})
        self.assertEqual(prefs.locations, ("Bandung",))

    def test_empty_location_list_means_all_indonesia(self):
        self.assertEqual(prefs_from_dict({"active": ["video"], "locations": []}, CATEGORIES).locations, ())

    def test_drops_unknown_active_names_and_falls_back_to_all(self):
        prefs = prefs_from_dict({"active": ["removed"]}, CATEGORIES)
        self.assertEqual(prefs.active, frozenset(CATEGORIES))

    def test_malformed_prefs_fall_back_to_defaults(self):
        prefs = prefs_from_dict({"active": "video", "custom": [1]}, CATEGORIES)
        self.assertEqual(prefs, Prefs(active=frozenset(CATEGORIES), custom={}, locations=None))


class SearchSelectionTest(unittest.TestCase):
    def test_returns_only_active_searches(self):
        searches = [Search("video editor", name="video"), Search("motion", name="motion")]
        self.assertEqual([s.name for s in active_searches(searches, frozenset({"motion"}))], ["motion"])

    def test_falls_back_to_all_when_nothing_matches(self):
        searches = [Search("video editor", name="video")]
        self.assertEqual(active_searches(searches, frozenset({"removed"})), searches)

    def test_custom_search_requires_all_words(self):
        search = custom_searches({"graphicdesigner": "graphic designer"})[0]

        self.assertEqual(search.name, "graphicdesigner")
        self.assertEqual(search.query, "graphic designer")
        self.assertEqual(search.title_must_include_all, ("graphic", "designer"))


if __name__ == "__main__":
    unittest.main()
