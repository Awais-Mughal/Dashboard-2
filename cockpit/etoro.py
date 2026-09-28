"""Read-only eToro market data adapter. Broker volume is unverified by default."""

import json
import math
import re
import uuid
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .provider import ProviderError


class EToro:
    def __init__(self, api_key, user_key, base_url="https://public-api.etoro.com"):
        if not api_key or not user_key:
            raise ValueError("Both eToro read API credentials are required")
        self.api_key, self.user_key, self.base_url = api_key, user_key, base_url.rstrip("/")
        self.ids = {}

    def _get(self, path, params=None):
        url = self.base_url + path + ("?" + urlencode(params, doseq=True) if params else "")
        request = Request(url, headers={"x-api-key": self.api_key, "x-user-key": self.user_key,
                                        "x-request-id": str(uuid.uuid4()), "Accept": "application/json"})
        try:
            with urlopen(request, timeout=15) as response:
                return json.load(response)
        except HTTPError as exc:
            raise ProviderError(f"eToro market-data request failed (HTTP {exc.code}); check API access") from None
        except (URLError, TimeoutError, ValueError) as exc:
            raise ProviderError(f"eToro market-data response failed ({type(exc).__name__})") from None

    def _instrument_id(self, symbol):
        if symbol not in self.ids:
            payload = self._get('/api/v2/market-data/instruments', {'symbols': symbol})
            items = payload if isinstance(payload, list) else payload.get('results', [])
            matches = [item for item in items if item.get('symbol', '').upper() == symbol]
            if len(matches) != 1 or not isinstance(matches[0].get('instrumentId'), int):
                raise ProviderError(f"eToro has no unique exact symbol match for {symbol}")
            self.ids[symbol] = matches[0]['instrumentId']
        return self.ids[symbol]

    def fetch_bars(self, symbol, start, end, timeframe='1Min'):
        if not re.fullmatch(r'[A-Z][A-Z0-9.\-]{0,11}', symbol):
            raise ValueError('Invalid stock symbol')
        if timeframe not in ('1Min', '1Day'):
            raise ValueError('Unsupported timeframe')
        try:
            lower = datetime.fromisoformat(start.replace('Z', '+00:00'))
            upper = datetime.fromisoformat(end.replace('Z', '+00:00'))
            if lower.tzinfo is None or upper.tzinfo is None or lower >= upper:
                raise ValueError()
        except (AttributeError, ValueError):
            raise ValueError('Invalid bounded time window') from None
        minutes = int((upper - lower).total_seconds() / 60)
        interval = 'OneMinute' if timeframe == '1Min' else 'OneDay'
        count = min(1000, max(1, minutes + 1 if timeframe == '1Min' else math.ceil(minutes / 1440) + 2))
        identifier = self._instrument_id(symbol)
        payload = self._get(f'/api/v1/market-data/instruments/{identifier}/history/candles/desc/{interval}/{count}')
        groups = payload.get('candles') if isinstance(payload, dict) else None
        if not isinstance(groups, list):
            raise ProviderError('eToro response lacks candle groups')
        result = []
        for group in groups:
            if group.get('instrumentId') != identifier or not isinstance(group.get('candles'), list):
                continue
            for candle in group['candles']:
                try:
                    timestamp = datetime.fromisoformat(candle['fromDate'].replace('Z', '+00:00'))
                    prices = [float(candle[key]) for key in ('open', 'high', 'low', 'close')]
                    if timestamp.tzinfo is None or not all(math.isfinite(p) and p > 0 for p in prices):
                        raise ValueError()
                except (KeyError, TypeError, ValueError):
                    raise ProviderError('eToro returned an invalid candle') from None
                if lower <= timestamp < upper:
                    result.append({'t': timestamp.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z'),
                                   'o': prices[0], 'h': prices[1], 'l': prices[2], 'c': prices[3],
                                   'v': None, 'vw': None})
        return sorted(result, key=lambda bar: bar['t'])
