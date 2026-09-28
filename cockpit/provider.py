"""Read-only Alpaca IEX bar adapter. No trade or account endpoints."""

import json
import re
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


class ProviderError(RuntimeError):
    pass


class AlpacaIEX:
    def __init__(self, key_id, secret, base_url="https://data.alpaca.markets"):
        if not key_id or not secret:
            raise ValueError("Both Alpaca data credentials are required")
        self.key_id, self.secret, self.base_url = key_id, secret, base_url.rstrip("/")

    def fetch_bars(self, symbol, start, end, timeframe="1Min"):
        if not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,11}", symbol):
            raise ValueError("Invalid stock symbol")
        if timeframe not in ("1Min", "1Day"):
            raise ValueError("Unsupported timeframe")
        if not start or not end or start >= end:
            raise ValueError("Invalid bounded time window")
        bars, token, seen = [], None, set()
        while True:
            params = {"start": start, "end": end, "timeframe": timeframe, "feed": "iex", "limit": "10000", "sort": "asc"}
            if token:
                params["page_token"] = token
            url = f"{self.base_url}/v2/stocks/{quote(symbol)}/bars?{urlencode(params)}"
            request = Request(url, headers={"APCA-API-KEY-ID": self.key_id, "APCA-API-SECRET-KEY": self.secret})
            try:
                with urlopen(request, timeout=12) as response:
                    payload = json.load(response)
            except HTTPError as exc:
                raise ProviderError(f"Alpaca data request failed (HTTP {exc.code}); check access and entitlement") from None
            except (URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
                raise ProviderError(f"Alpaca data response failed ({type(exc).__name__})") from None
            if not isinstance(payload.get("bars"), list):
                raise ProviderError("Alpaca response lacks bars")
            bars.extend(payload["bars"])
            token = payload.get("next_page_token")
            if not token:
                return bars
            if token in seen or len(seen) >= 50:
                raise ProviderError("Alpaca pagination did not terminate")
            seen.add(token)
