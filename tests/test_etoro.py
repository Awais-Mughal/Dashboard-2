import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from cockpit.etoro import EToro, ProviderError


class EToroTests(unittest.TestCase):
    def setUp(self):
        self.requests = []
        outer = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                outer.requests.append((self.path, {k.lower(): v for k, v in self.headers.items()}))
                if self.path.startswith('/api/v2/market-data/instruments'):
                    body = {'results': [{'instrumentId': 42, 'symbol': 'SPY', 'type': 'ETF'}], 'pagination': {'hasNext': False}}
                else:
                    body = {'interval': 'OneMinute', 'candles': [{'instrumentId': 42, 'candles': [
                        {'fromDate': '2026-09-24T13:30:00Z', 'open': 100, 'high': 102, 'low': 99, 'close': 101, 'volume': 0}
                    ]}]}
                data = json.dumps(body).encode()
                self.send_response(200)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.client = EToro('public-secret', 'user-secret', f'http://127.0.0.1:{self.server.server_port}')

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_exact_symbol_and_zero_volume_remain_unverified(self):
        bars = self.client.fetch_bars('SPY', '2026-09-24T13:00:00Z', '2026-09-24T14:00:00Z')
        self.assertEqual(bars[0]['c'], 101)
        self.assertIsNone(bars[0]['v'])
        self.assertIsNone(bars[0]['vw'])
        self.assertEqual(len(self.requests), 2)
        self.assertTrue(all(req[1].get('x-api-key') == 'public-secret' and req[1].get('x-user-key') == 'user-secret' and req[1].get('x-request-id') for req in self.requests))
        self.assertNotEqual(self.requests[0][1]['x-request-id'], self.requests[1][1]['x-request-id'])

    def test_invalid_symbol_rejected_before_network(self):
        with self.assertRaises(ValueError): self.client.fetch_bars('../orders', 'a', 'b')
        self.assertFalse(self.requests)


if __name__ == '__main__': unittest.main()
