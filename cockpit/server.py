"""Local prototype API and static-file server."""

import json
import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from .metrics import compute_snapshot, breadth, parse_time
from .provider import AlpacaIEX, ProviderError
from .etoro import EToro
from .sample import sample_series, STOCKS, SECTORS, BENCHMARKS
from .storage import Store

WEB = Path(__file__).resolve().parent.parent / "web"


class AppState:
    def __init__(self, db_path, key_id=None, secret=None, provider=None, etoro_key=None, etoro_user_key=None):
        self.store = Store(db_path)
        self.provider = provider or (AlpacaIEX(key_id, secret) if key_id and secret else None)
        self.etoro = EToro(etoro_key, etoro_user_key) if etoro_key and etoro_user_key else None
        self.selected = 'sample'
        self.series = sample_series()
        self.mode = "synthetic_example"
        self.symbols = list(self.series)
        self.stocks = list(STOCKS)
        self.lock = threading.RLock()
        self.probe_lock = threading.Lock()
        self.refresh_error = None

    def refresh_once(self):
        if self.selected == 'sample' or not self.probe_lock.acquire(blocking=False):
            return
        try:
            self.probe()
            self.refresh_error = None
        except (ProviderError, ValueError) as exc:
            self.refresh_error = str(exc)
        finally:
            self.probe_lock.release()

    def select_provider(self, name):
        if name not in ('sample', 'alpaca', 'etoro'):
            raise ValueError('Unknown data provider')
        if name != 'sample' and getattr(self, 'provider' if name == 'alpaca' else 'etoro') is None:
            raise ValueError(f'Configure {name} server credentials before connecting')
        with self.lock:
            self.selected = name
            if name == 'sample':
                self.series = sample_series()
                self.symbols = list(self.series)
                self.stocks = list(STOCKS)
                self.mode = 'synthetic_example'
                self.refresh_error = None
        return {'selected': self.selected, 'mode': self.mode}

    def snapshots(self):
        with self.lock:
            series, mode, symbols = self.series, self.mode, self.symbols
            usable_ends = [parse_time(data["minute"][-1]["t"]) + timedelta(minutes=1)
                           for data in series.values() if data["minute"]]
            cutoff = min(usable_ends) if usable_ends else datetime.now(timezone.utc)
            feed = "synthetic_example" if mode == "synthetic_example" else "etoro:unverified_volume" if mode == "recorded_etoro" else "alpaca:iex"
            result = {s: compute_snapshot(s, series[s], series.get(BENCHMARKS[s]) if s in BENCHMARKS else None, feed=feed, as_of=cutoff)
                      for s in symbols}
            threshold = timedelta(minutes=5 if mode == 'recorded_etoro' else 30)
            if mode != 'synthetic_example' and datetime.now(timezone.utc) - cutoff > threshold:
                for snapshot in result.values():
                    snapshot['status'] = 'stale'
                    snapshot.setdefault('issues', []).append('old_cutoff')
            return result

    def probe(self):
        selected = self.selected
        chosen = self.etoro if selected == 'etoro' else self.provider
        if chosen is None:
            raise ValueError('Select and configure a data provider before loading')
        end = datetime.now(timezone.utc) - timedelta(minutes=16 if selected != 'etoro' else 2)
        start = end - timedelta(days=7)
        daily_start = end - timedelta(days=35)
        fresh = {}
        for symbol in ("SPY", "QQQ", "AAPL", "NVDA", "XLK"):
            minute = chosen.fetch_bars(symbol, start.isoformat(), end.isoformat())
            daily = chosen.fetch_bars(symbol, daily_start.isoformat(), end.isoformat(), "1Day")
            if minute:
                fresh[symbol] = {"minute": minute, "daily": daily}
        if not all(s in fresh for s in ("SPY", "QQQ", "AAPL", "NVDA")):
            raise ProviderError("Probe returned incomplete benchmark/stock bars; remaining in example mode")
        common_cutoff = min(parse_time(data["minute"][-1]["t"]) + timedelta(minutes=1) for data in fresh.values())
        required = ("SPY", "QQQ", "AAPL", "NVDA")
        feed = 'etoro:unverified_volume' if selected == 'etoro' else 'alpaca:iex'
        checks = [compute_snapshot(symbol, fresh[symbol], feed=feed, as_of=common_cutoff) for symbol in required]
        if any(check.get("last") is None or check.get("previous_close") is None for check in checks):
            raise ProviderError("Probe lacks comparable completed regular-session and previous-close bars; remaining in example mode")
        for symbol, data in fresh.items():
            self.store.save_bars(symbol, feed, "1Min", data["minute"])
            self.store.save_bars(symbol, feed, "1Day", data["daily"])
        with self.lock:
            if self.selected != selected:
                raise ProviderError('Data provider changed during refresh; discard old result')
            self.series = fresh
            self.symbols = list(fresh)
            self.stocks = [s for s in ("AAPL", "NVDA") if s in fresh]
            self.mode = "recorded_etoro" if selected == 'etoro' else "recorded_iex_delayed"
            self.refresh_error = None
        return {"mode": self.mode, "symbols": self.symbols, "cutoff": common_cutoff.isoformat().replace("+00:00", "Z"), "note": "eToro price candles · volume unverified · no streaming" if selected == 'etoro' else "IEX venue only · historical request ends at least 16 minutes before request time · no streaming"}

    def outcomes(self, item):
        snapshot = item['snapshot']
        symbol, feed, cutoff, price = (snapshot.get(k) for k in ('symbol', 'feed', 'cutoff', 'last'))
        if not all((symbol, feed, cutoff, price)):
            return {key: {'status': 'unavailable'} for key in ('15m', '60m', 'close')}
        start = parse_time(cutoff)
        bars = self.store.get_bars(symbol, feed, '1Min', cutoff)
        results = {}
        close = start.astimezone(ZoneInfo('America/New_York')).replace(hour=16, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
        for label, minutes in (('15m', 15), ('60m', 60), ('close', None)):
            target = start + timedelta(minutes=minutes) if minutes else close
            deadline = min(target, close)
            truncated = target > close
            eligible = [b for b in bars if parse_time(b['t']) >= start and parse_time(b['t']) + timedelta(minutes=1) <= deadline]
            complete = bool(eligible) and parse_time(eligible[-1]['t']) + timedelta(minutes=1) >= deadline
            expected = max(0, int((deadline - start).total_seconds() / 60))
            has_gaps = bool(eligible) and len(eligible) < expected
            results[label] = {'status': 'partial' if complete and has_gaps else 'truncated' if complete and truncated else 'valid' if complete else 'pending', 'return_pct': 100 * (eligible[-1]['c'] / price - 1) if eligible else None,
                              'highest': max((b['h'] for b in eligible), default=None), 'lowest': min((b['l'] for b in eligible), default=None),
                              'bars': len(eligible), 'deadline': deadline.isoformat().replace('+00:00', 'Z')}
        return results


def make_handler(state):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send_json(self, value, status=200):
            data = json.dumps(value, allow_nan=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            path = urlparse(self.path).path
            if path in ("/", "/app.js", "/style.css"):
                filename = "index.html" if path == "/" else path[1:]
                data = (WEB / filename).read_bytes()
                mime = {"index.html": "text/html", "app.js": "text/javascript", "style.css": "text/css"}[filename]
                self.send_response(200)
                self.send_header("Content-Type", mime + "; charset=utf-8")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            if path == "/api/status":
                return self.send_json({"mode": state.mode, "symbols": state.symbols, "has_credentials": bool(state.provider),
                                       "selected": state.selected, "providers": {"sample": True, "alpaca": bool(state.provider), "etoro": bool(state.etoro)}, "refresh_error": state.refresh_error,
                                       "capabilities": {"live_stream": False, "full_market_volume": False, "rvol": False},
                                       "message": "Synthetic example data; no live market connection" if state.mode == "synthetic_example" else "Recorded eToro price candles; volume unverified" if state.mode == 'recorded_etoro' else "Recorded Alpaca IEX bars; limited venue and delayed cutoff"})
            if path == "/api/observations":
                return self.send_json({"items": [{**item, 'outcomes': state.outcomes(item)} for item in state.store.list_observations()]})
            if path == '/api/watchlist':
                return self.send_json({'symbols': state.store.setting('watchlist', ['AAPL', 'NVDA'])})
            if path == '/api/events':
                return self.send_json({'items': state.store.setting('events', []), 'status': 'imported' if state.store.setting('events') else 'unavailable'})
            if path in ("/api/market", "/api/scanner") or re.fullmatch(r"/api/stocks/[A-Z0-9.\-]+", path):
                snapshots = state.snapshots()
                cutoff = min((s["cutoff"] for s in snapshots.values()), default=None)
                common = {"mode": state.mode, "cutoff": cutoff}
                if path == "/api/market":
                    return self.send_json({**common, "benchmarks": {k: snapshots[k] for k in ("SPY", "QQQ", "IWM") if k in snapshots},
                                           "sectors": [{"symbol": k, "name": v, "snapshot": snapshots[k]} for k, v in SECTORS.items() if k in snapshots],
                                           "breadth": breadth([snapshots[k] for k in state.stocks if k in snapshots])})
                if path == "/api/scanner":
                    return self.send_json({**common, "items": [snapshots[k] for k in state.stocks if k in snapshots]})
                symbol = path.rsplit("/", 1)[1]
                if symbol not in snapshots:
                    return self.send_json({"error": "Unknown instrument"}, 404)
                with state.lock:
                    bars = state.series[symbol]["minute"]
                    chart = [b for b in bars if parse_time(b["t"]) + timedelta(minutes=1) <= parse_time(snapshots[symbol]["cutoff"])]
                return self.send_json({**common, "snapshot": snapshots[symbol], "bars": chart[-90:], "benchmark": BENCHMARKS.get(symbol)})
            return self.send_json({"error": "Not found"}, 404)

        def do_POST(self):
            path = urlparse(self.path).path
            if path not in ("/api/probe", "/api/observations", '/api/provider', '/api/watchlist', '/api/events'):
                return self.send_json({"error": "Not found"}, 404)
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                return self.send_json({"error": "JSON required"}, 415)
            try:
                length = int(self.headers.get("Content-Length", 0))
                if length < 2 or length > 4096:
                    return self.send_json({"error": "Invalid request size"}, 400)
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise ValueError("JSON object required")
                if path == "/api/probe":
                    return self.send_json(state.probe())
                if path == '/api/provider':
                    return self.send_json(state.select_provider(body.get('provider')))
                if path == '/api/watchlist':
                    symbols = body.get('symbols')
                    if not isinstance(symbols, list) or len(symbols) > 100 or len(set(map(str, symbols))) != len(symbols) or any(not isinstance(s, str) or s not in state.symbols for s in symbols):
                        raise ValueError('Watchlist requires unique available symbols')
                    state.store.set_setting('watchlist', symbols)
                    return self.send_json({'symbols': symbols})
                if path == '/api/events':
                    items = body.get('items')
                    if not isinstance(items, list) or len(items) > 30:
                        raise ValueError('Events must be a list of up to 30 records')
                    normalized = []
                    for item in items:
                        if not isinstance(item, dict) or not all(isinstance(item.get(k), str) and item[k] for k in ('title', 'type', 'scheduled_at', 'timezone', 'source_url')):
                            raise ValueError('Event requires title, type, schedule, timezone and source URL')
                        parse_time(item['scheduled_at'])
                        if not item['source_url'].startswith('https://') or not isinstance(item.get('symbols'), list) or any(s not in state.symbols for s in item['symbols']):
                            raise ValueError('Event requires HTTPS source and available symbols')
                        normalized.append({**item, 'retrieved_at': datetime.now(timezone.utc).isoformat()})
                    state.store.set_setting('events', normalized)
                    return self.send_json({'items': normalized})
                symbol, note = body.get("symbol"), body.get("note", "")
                if symbol not in state.symbols or not isinstance(note, str):
                    raise ValueError("Select an available instrument and text note")
                snapshot = state.snapshots()[symbol]
                created = state.store.save_observation(snapshot, note)
                state.store.save_bars(symbol, snapshot['feed'], '1Min', state.series[symbol]['minute'])
                return self.send_json(created, 201)
            except (ValueError, json.JSONDecodeError) as exc:
                return self.send_json({"error": str(exc)}, 409 if path in ('/api/probe', '/api/provider') else 400)
            except ProviderError as exc:
                return self.send_json({"error": str(exc)}, 502)

    return Handler


def main():
    host = "127.0.0.1"
    port = int(os.getenv("COCKPIT_PORT", "8765"))
    path = Path(os.getenv("COCKPIT_DB", "./data/cockpit.sqlite"))
    state = AppState(path, os.getenv("ALPACA_API_KEY_ID"), os.getenv("ALPACA_API_SECRET_KEY"),
                     etoro_key=os.getenv('ETORO_API_KEY'), etoro_user_key=os.getenv('ETORO_USER_KEY'))
    def refresh_loop():
        while True:
            time.sleep(120)
            state.refresh_once()
    threading.Thread(target=refresh_loop, daemon=True, name='market-refresh').start()
    server = ThreadingHTTPServer((host, port), make_handler(state))
    print(f"Cockpit at http://{host}:{port} — {state.mode}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
