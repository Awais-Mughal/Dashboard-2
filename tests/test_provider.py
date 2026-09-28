import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from cockpit.provider import AlpacaIEX, ProviderError


class TestHandler(BaseHTTPRequestHandler):
    seen = []
    def do_GET(self):
        type(self).seen.append((self.path, dict(self.headers)))
        if "INVALID" in self.path:
            self.send_response(403)
            self.end_headers()
            return
        token = "page_token=next" in self.path
        payload = {"bars": [{"t": "2026-09-24T13:31:00Z" if token else "2026-09-24T13:30:00Z", "o": 1, "h": 2, "l": 1, "c": 2, "v": 100, "vw": 1.5}], "next_page_token": None if token else "next"}
        result = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(result)))
        self.end_headers()
        self.wfile.write(result)

    def log_message(self, *args):
        pass


class ProviderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), TestHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        TestHandler.seen = []
        self.provider = AlpacaIEX("id-test", "secret-test", base_url=f"http://127.0.0.1:{self.server.server_port}")

    def test_fetch_paginates_and_sends_iex_auth(self):
        bars = self.provider.fetch_bars("AAPL", "2026-09-24T13:30:00Z", "2026-09-24T13:33:00Z")
        self.assertEqual(len(bars), 2)
        self.assertIn("feed=iex", TestHandler.seen[0][0])
        self.assertEqual({k.lower(): v for k, v in TestHandler.seen[0][1].items()}["apca-api-key-id"], "id-test")
        self.assertIn("page_token=next", TestHandler.seen[1][0])

    def test_auth_failure_is_visible(self):
        with self.assertRaises(ProviderError):
            self.provider.fetch_bars("INVALID", "2026-09-24", "2026-09-25")

    def test_symbol_validation_blocks_path_injection(self):
        with self.assertRaises(ValueError):
            self.provider.fetch_bars("../secret", "2026-09-24", "2026-09-25")


if __name__ == "__main__": unittest.main()
