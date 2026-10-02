import unittest

from loker_bot.state import StateClient, StateError


class FakeTransport:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def __call__(self, method, url, headers, payload=None):
        self.calls.append((method, url, headers, payload))
        if self.error:
            raise self.error
        return self.response


class StateClientTest(unittest.TestCase):
    def test_load_returns_prefs_seen_and_config_with_auth_header(self):
        transport = FakeTransport({"prefs": {"active": ["video"]}, "seen": {"A:1": "t"}, "config": None})
        client = StateClient("https://w.example/", "s3cret", transport)

        state = client.load()

        self.assertEqual(state.seen, {"A:1": "t"})
        self.assertEqual(state.prefs_raw, {"active": ["video"]})
        method, url, headers, _ = transport.calls[0]
        self.assertEqual((method, url), ("GET", "https://w.example/state"))
        self.assertEqual(headers["Authorization"], "Bearer s3cret")

    def test_save_sends_seen_and_config_only(self):
        transport = FakeTransport(None)
        client = StateClient("https://w.example", "s3cret", transport)

        client.save(seen={"A:1": "t"}, config={"builtin": ["video"], "default_locations": []})

        method, url, _, payload = transport.calls[0]
        self.assertEqual((method, url), ("PUT", "https://w.example/state"))
        self.assertEqual(set(payload), {"seen", "config"})

    def test_wraps_transport_errors(self):
        client = StateClient("https://w.example", "s", FakeTransport(error=OSError("down")))
        with self.assertRaises(StateError):
            client.load()

    def test_rejects_malformed_response(self):
        client = StateClient("https://w.example", "s", FakeTransport(["not", "a", "dict"]))
        with self.assertRaises(StateError):
            client.load()


if __name__ == "__main__":
    unittest.main()
