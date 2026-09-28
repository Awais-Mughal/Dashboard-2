import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from cockpit.server import AppState, make_handler
from cockpit.provider import ProviderError


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = AppState(Path(self.tmp.name) / "data.sqlite", key_id=None, secret=None)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.state))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def get(self, path):
        with urlopen(self.base + path) as response:
            return json.load(response)

    def post(self, path, value):
        request = Request(self.base + path, data=json.dumps(value).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request) as response:
            return json.load(response)

    def test_sample_mode_is_explicit_on_every_market_response(self):
        self.assertEqual(self.get("/api/status")["mode"], "synthetic_example")
        self.assertEqual(self.get("/api/market")["mode"], "synthetic_example")
        self.assertEqual(self.get("/api/scanner")["mode"], "synthetic_example")
        detail = self.get("/api/stocks/NVDA")
        self.assertEqual(detail["mode"], "synthetic_example")
        self.assertEqual(detail["snapshot"]["feed"], "synthetic_example")

    def test_unknown_instrument_returns_404(self):
        with self.assertRaises(HTTPError) as result:
            self.get("/api/stocks/DOESNOTEXIST")
        self.assertEqual(result.exception.code, 404)

    def test_observation_post_persists_server_snapshot(self):
        created = self.post("/api/observations", {"symbol": "NVDA", "note": "Watch opening high", "snapshot": {"last": 999999}})
        self.assertNotEqual(created["snapshot"]["last"], 999999)
        self.assertEqual(self.get("/api/observations")["items"][0]["id"], created["id"])

    def test_probe_without_credentials_exposes_error_without_key(self):
        request = Request(self.base + "/api/probe", data=b"{}", method="POST", headers={"Content-Type": "application/json"})
        with self.assertRaises(HTTPError) as result:
            urlopen(request)
        self.assertEqual(result.exception.code, 409)
        self.assertNotIn("secret", self.get("/api/status"))

    def test_premarket_only_probe_keeps_example_mode(self):
        class PremarketProvider:
            def fetch_bars(self, symbol, start, end, timeframe="1Min"):
                if timeframe == "1Day":
                    return [{"t": "2026-09-23T20:00:00Z", "o": 99, "h": 101, "l": 98, "c": 100, "v": 1000}]
                return [{"t": "2026-09-24T12:00:00Z", "o": 101, "h": 102, "l": 100, "c": 101, "v": 100, "vw": 101}]
        self.state.provider = PremarketProvider()
        with self.assertRaises(ProviderError):
            self.state.probe()
        self.assertEqual(self.state.mode, "synthetic_example")

    def test_provider_selection_requires_configured_credentials(self):
        with self.assertRaises(HTTPError) as result:
            self.post('/api/provider', {'provider': 'etoro'})
        self.assertEqual(result.exception.code, 409)
        self.assertEqual(self.post('/api/provider', {'provider': 'sample'})['mode'], 'synthetic_example')

    def test_watchlist_roundtrip_and_rejects_unknown_symbol(self):
        original = self.get('/api/watchlist')['symbols']
        self.assertTrue(original)
        updated = self.post('/api/watchlist', {'symbols': ['AAPL', 'NVDA']})
        self.assertEqual(updated['symbols'], ['AAPL', 'NVDA'])
        self.assertEqual(self.get('/api/watchlist')['symbols'], ['AAPL', 'NVDA'])
        with self.assertRaises(HTTPError):
            self.post('/api/watchlist', {'symbols': ['INVALID']})

    def test_events_are_imported_with_source_and_returned(self):
        item = {'title': 'CPI release', 'type': 'economic', 'scheduled_at': '2026-10-13T12:30:00Z', 'timezone': 'America/New_York', 'source_url': 'https://www.bls.gov/schedule/news_release/cpi.htm', 'symbols': ['SPY']}
        self.post('/api/events', {'items': [item]})
        self.assertEqual(self.get('/api/events')['items'][0]['title'], 'CPI release')
        self.assertEqual(self.get('/api/events')['items'][0]['symbols'], ['SPY'])

    def test_observation_outcome_excludes_overlapping_bar(self):
        created = self.post('/api/observations', {'symbol': 'NVDA', 'note': 'baseline'})
        outcome = self.get('/api/observations')["items"][0]['outcomes']['15m']
        self.assertIn(outcome['status'], ('pending', 'valid', 'truncated'))
        self.assertEqual(created['id'], self.get('/api/observations')['items'][0]['id'])

    def test_missing_minute_prevents_valid_outcome(self):
        snapshot = {'symbol': 'AAPL', 'feed': 'unit:feed', 'cutoff': '2026-09-24T13:30:00Z', 'last': 100}
        item = self.state.store.save_observation(snapshot)
        self.state.store.save_bars('AAPL', 'unit:feed', '1Min', [
            {'t': '2026-09-24T13:30:00Z', 'o': 100, 'h': 101, 'l': 99, 'c': 101},
            {'t': '2026-09-24T13:44:00Z', 'o': 101, 'h': 103, 'l': 100, 'c': 102}])
        self.assertEqual(self.state.outcomes(item)['15m']['status'], 'partial')

    def test_background_refresh_failure_preserves_previous_series_and_reports_error(self):
        class Broken:
            def fetch_bars(self, *args):
                raise ProviderError('temporary market data failure')
        original = self.state.series
        self.state.provider = Broken()
        self.state.selected = 'alpaca'
        self.state.refresh_once()
        self.assertIs(self.state.series, original)
        self.assertIn('temporary', self.state.refresh_error)

    def test_recorded_old_data_is_marked_stale(self):
        self.state.mode = 'recorded_etoro'
        snapshots = self.state.snapshots()
        self.assertEqual(snapshots['AAPL']['status'], 'stale')

    def test_outcome_window_crossing_close_is_truncated(self):
        snapshot = {'symbol': 'AAPL', 'feed': 'unit:feed', 'cutoff': '2026-09-24T19:59:00Z', 'last': 100}
        item = self.state.store.save_observation(snapshot)
        self.state.store.save_bars('AAPL', 'unit:feed', '1Min', [
            {'t': '2026-09-24T19:59:00Z', 'o': 100, 'h': 101, 'l': 99, 'c': 101}])
        self.assertEqual(self.state.outcomes(item)['15m']['status'], 'truncated')


if __name__ == "__main__": unittest.main()
