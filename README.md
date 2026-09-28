# Market Learning Cockpit

A private, read-only US equity learning dashboard. Run locally with Python 3.12+ and no third-party packages. Its default dataset is **synthetic** and clearly labeled. This repository currently has no configured Git remote or deployment target.

## Run

```bash
python -m cockpit.server
```

Open `http://127.0.0.1:8765`. Set `COCKPIT_DB` for a persistent SQLite path and `COCKPIT_PORT` for another local port. The server intentionally binds to localhost. Keep an existing authenticated HTTPS reverse proxy in front of it if deployed; the application itself has no user authentication.

## Connect eToro or Alpaca

Create an eToro key with **Read** permission. Set both keys in the server environment and restart:

```bash
export ETORO_API_KEY='your-public-api-key'
export ETORO_USER_KEY='your-read-user-key'
python -m cockpit.server
```

Choose **eToro** in the banner and click **Load recorded data**. Credentials stay on the server. The adapter only calls the instrument lookup and historical candle GET endpoints; it never calls account or order endpoints. A unique exact symbol match is required. The read-only probe requests SPY, QQQ, AAPL, NVDA, and XLK, verifies price bars and a previous daily close, then switches all charts to a separate `etoro:unverified_volume` series. After connection, the server refreshes the recorded series every two minutes, and the page checks status every 45 seconds. A failed refresh preserves the last recorded dataset and displays the failure. **These are recorded candles, not a verified live stream.**

The eToro documentation includes candles with `volume: 0` and gives no verified US-equity consolidated volume semantics. This adapter deliberately discards the volume field: VWAP, RVOL and volume breadth are unavailable. The price source may also differ from consolidated trade prices. Do not interpret these candles as exchange prints until a real-account capability probe establishes their meaning. The endpoint returns at most 1,000 candles per request; this adapter does not claim 20 comparable sessions of minute history.

Alternatively configure `ALPACA_API_KEY_ID` and `ALPACA_API_SECRET_KEY` to select **Alpaca IEX**. The historical request ends at least 16 minutes before now; IEX is limited venue coverage. No trade execution is implemented for either provider.

## Features

- Today, Scanner, Stock Explorer, contextual Learn, and Observations.
- Prior-close and since-open return, benchmark-relative percentage points at a matching bar end, feed opening gap, previous-day, premarket, and 5/20-session reference levels when the input history exists.
- Fixed tracked-stock breadth, including price-valid names whose volume is missing.
- Persistent local watchlist; watchlist-only scanner filter.
- Import a small sourced calendar with `POST /api/events` using `{"items":[{"title":"...","type":"economic","scheduled_at":"2026-10-13T12:30:00Z","timezone":"America/New_York","source_url":"https://...","symbols":["SPY"]}]}`. An empty calendar means unavailable, not no events.
- Immutable saved snapshot and note. Recorded-bar outcome fields for 15 minutes, 60 minutes, and same-session close, with pending/partial status. Outcome returns are observations, not fills or P/L. Subsequent bars arrive on later refreshes.
- Explicit source labels, cutoff, missing inputs and refresh failures. SQLite keeps provider-separated bars and notes.

## Verification

```bash
python -m unittest discover -s tests -v
node --check web/app.js
```

The eToro tests run against a local HTTP fixture using the documented response envelope. A real eToro account and the deployed site are **not** exercised by these tests.

## Remaining release gates

The broader v0.2 spec (`market_learning_cockpit_mvp_v0_2.md`) also calls for a verified exchange calendar, split-consistent prices, bar revisions, same-time RVOL/ATR with sufficient eligible history, reliable live streaming with reconnect/backfill, point-in-time outcome revisions, richer event acquisition and production backup/restore. Those need real feed entitlement and data semantics. This code remains a recorded-study MVP build, not a certified live trading dashboard. Before integrating into an existing online deployment, review its actual repository, authentication, reverse proxy, secrets handling and backup setup.

Official eToro documentation: [authentication](https://api-portal.etoro.com/core/getting-started/authentication), [symbol lookup](https://api-portal.etoro.com/api-reference/market-data/search-for-securities-instruments-by-id-or-symbol), [candle history](https://api-portal.etoro.com/api-reference/market-data/get-instrument-candle-history).
