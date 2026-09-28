"""Deterministic, visibly synthetic example market; never claimed as real prices."""

from datetime import datetime, timedelta, timezone


MARKET = ("SPY", "QQQ", "IWM")
STOCKS = ("AAPL", "MSFT", "NVDA", "AMD", "AVGO", "AMZN", "META", "GOOGL", "TSLA", "NFLX",
          "PLTR", "JPM", "BAC", "WFC", "XOM", "CVX", "LLY", "UNH", "CAT", "BA")
SECTORS = {"XLK": "Technology", "XLF": "Financials", "XLE": "Energy", "XLV": "Health care",
           "XLI": "Industrials", "XLY": "Consumer discretionary", "XLP": "Consumer staples",
           "XLU": "Utilities", "XLB": "Materials", "XLC": "Communication services",
           "XLRE": "Real estate", "SMH": "Semiconductors · theme"}
SYMBOLS = MARKET + tuple(SECTORS) + STOCKS
BENCHMARKS = {
    "AAPL": "XLK", "MSFT": "XLK", "PLTR": "XLK",
    "NVDA": "SMH", "AMD": "SMH", "AVGO": "SMH",
    "AMZN": "XLY", "TSLA": "XLY", "META": "XLC", "GOOGL": "XLC", "NFLX": "XLC",
    "JPM": "XLF", "BAC": "XLF", "WFC": "XLF", "XOM": "XLE", "CVX": "XLE",
    "LLY": "XLV", "UNH": "XLV", "CAT": "XLI", "BA": "XLI",
}


def sample_series():
    starts = {symbol: round(35 + ((sum(map(ord, symbol)) * 37) % 500), 2) for symbol in SYMBOLS}
    starts.update({"SPY": 560, "QQQ": 480, "IWM": 215, "XLK": 240, "XLF": 50, "XLE": 85,
                   "SMH": 280, "NVDA": 130, "AAPL": 225, "AMD": 160, "MSFT": 430,
                   "JPM": 210, "TSLA": 250})
    slopes = {symbol: (((sum(map(ord, symbol)) * 11) % 17) - 8) / 40 for symbol in SYMBOLS}
    slopes.update({"SPY": .07, "QQQ": .14, "IWM": -.06, "XLK": .10, "XLF": -.04,
                   "XLE": -.08, "SMH": .24, "NVDA": .22, "AAPL": .04, "AMD": .35,
                   "MSFT": .10, "JPM": -.07, "TSLA": .17})
    start = datetime(2026, 9, 24, 13, 30, tzinfo=timezone.utc)
    prior = datetime(2026, 9, 23, 20, tzinfo=timezone.utc)
    result = {}
    for pos, (symbol, price) in enumerate(starts.items()):
        minute = []
        previous = price
        for index in range(45):
            change = slopes[symbol] + ((index * 7 + pos * 5) % 9 - 4) * price * .0001
            close = round(previous + change, 3)
            volume = 9500 + pos * 1400 + ((index * 19 + pos * 13) % 7) * 2800
            minute.append({"t": (start + timedelta(minutes=index)).isoformat().replace("+00:00", "Z"),
                           "o": previous, "h": round(max(previous, close) + .08, 3),
                           "l": round(min(previous, close) - .08, 3), "c": close,
                           "v": volume, "vw": round((previous + close) / 2, 3)})
            previous = close
        result[symbol] = {"minute": minute, "daily": [{"t": prior.isoformat().replace("+00:00", "Z"),
                          "o": price - 1, "h": price + 2, "l": price - 3,
                          "c": round(price - (1.5 if slopes[symbol] > 0 else -.8), 3), "v": 1_000_000}]}
    return result
