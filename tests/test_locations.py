import unittest

from loker_bot.locations import handle_location_command

JABO = ("Jakarta", "Tangerang")


class LocationCommandTest(unittest.TestCase):
    def test_tambah_adds_multi_word_location(self):
        locations, reply = handle_location_command("/tambahlokasi Tangerang Selatan", JABO)

        self.assertEqual(locations, ("Jakarta", "Tangerang", "Tangerang Selatan"))
        self.assertIn("Tangerang Selatan", reply)

    def test_tambah_capitalizes_and_ignores_duplicates(self):
        locations, _ = handle_location_command("/tambahlokasi jakarta", JABO)
        self.assertEqual(locations, JABO)

    def test_tambah_from_all_indonesia_starts_new_list(self):
        locations, _ = handle_location_command("/tambahlokasi bandung", ())
        self.assertEqual(locations, ("Bandung",))

    def test_hapus_removes_case_insensitive(self):
        locations, _ = handle_location_command("/hapuslokasi TANGERANG", JABO)
        self.assertEqual(locations, ("Jakarta",))

    def test_hapus_refuses_last_location(self):
        locations, reply = handle_location_command("/hapuslokasi jakarta", ("Jakarta",))

        self.assertEqual(locations, ("Jakarta",))
        self.assertIn("/semualokasi", reply)

    def test_hapus_unknown_location_keeps_list(self):
        locations, reply = handle_location_command("/hapuslokasi bali", JABO)

        self.assertEqual(locations, JABO)
        self.assertIn("Bali", reply)

    def test_semua_means_all_indonesia(self):
        locations, reply = handle_location_command("/semualokasi", JABO)

        self.assertEqual(locations, ())
        self.assertIn("Seluruh Indonesia", reply)

    def test_lokasi_shows_current_without_change(self):
        locations, reply = handle_location_command("/lokasi", JABO)

        self.assertEqual(locations, JABO)
        self.assertIn("Jakarta", reply)
        self.assertIn("/tambahlokasi", reply)

    def test_tambah_without_name_shows_hint(self):
        locations, reply = handle_location_command("/tambahlokasi", JABO)

        self.assertEqual(locations, JABO)
        self.assertIn("/tambahlokasi bandung", reply)

    def test_returns_none_for_other_commands(self):
        self.assertIsNone(handle_location_command("/kategori", JABO))


if __name__ == "__main__":
    unittest.main()
