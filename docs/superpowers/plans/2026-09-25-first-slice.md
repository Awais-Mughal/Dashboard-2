# Market Learning Cockpit First Slice Implementation Plan

> For agentic workers: execute natively with test-first development. This plan intentionally covers a working vertical slice of the approved v0.2 design; later stages have separate gates.

**Goal:** Deliver a runnable private local dashboard with a working Alpaca read-only probe, labeled example mode, core calculations, and persistent observations.

**Architecture:** A standard-library Python HTTP service serves static frontend files and JSON APIs. A read-only Alpaca adapter fetches bounded IEX historical bars when credentials are supplied. SQLite persists normalized bars and user observations. No live-order capability exists. The stage remains a local prototype until authenticated data and long-session recovery can be validated.

**Tech stack:** Python 3.12 standard library; SQLite; HTML/CSS/ES modules; unittest.

**Spec:** `../market_learning_cockpit_mvp_v0_2.md` (packaged at project root).

**Rationale for temporary stack:** Runtime lacks FastAPI, SQLAlchemy, React and PostgreSQL. The API and data model isolate backend transport/storage from metric logic. Replacing HTTP/SQLite with target components is a later task after actual feed validation.

## Global constraints

- US equities/ETFs only; private local access by default.
- No order endpoint or broker trading permissions.
- All sample data explicitly labeled synthetic.
- Missing values remain null; no mixing of providers or fabricated market data.
- Initial live integration is a manual read-only probe, not a streaming release.
- Source/feed and time cutoff accompany computed metrics.

## Review focus

- Auth failure must never fall back to sample data with a live label.
- Missing volume must not calculate VWAP or RVOL.
- Bars from future dates or mixed feeds must not silently affect the snapshot.
- Observation snapshots retain original evidence when market data changes.
- Local HTTP service must not expose credentials or be bound publicly by default.

## Tasks

### Task 1: Calculation core

**Files:** `cockpit/metrics.py`, `tests/test_metrics.py`

**Interface:** `compute_snapshot(symbol, bars, benchmark_bars=None, feed='sample', as_of=None) -> dict`, `breadth(snapshots) -> dict`.

- [x] Write hand-computed tests: returns since close/open, percentage-point relative return, bar VWAP, null on missing volume, previous-session high, breadth denominator and cutoff exclusion.
- [x] Run `python -m unittest discover -s tests -v` and confirm missing module/failing test.
- [x] Implement calculations over normalized dict bars.
- [x] Run the suite and confirm all tests pass.

### Task 2: Read-only source and persistence

**Files:** `cockpit/provider.py`, `cockpit/storage.py`, `tests/test_provider.py`, `tests/test_storage.py`

**Interface:** `AlpacaIEX.fetch_bars(symbol, start, end, timeframe='1Min') -> list[dict]`; `Store.save_bars`, `.get_bars`, `.save_observation`, `.list_observations`.

- [x] Write failing tests with a local HTTP test server for headers, pagination and rejection; SQLite tests for idempotent bars and immutable observation JSON.
- [x] Implement bounded HTTP IEX client with timeout, pagination and credential validation, plus SQLite store.
- [x] Run the whole suite.

### Task 3: API and usable dashboard

**Files:** `cockpit/server.py`, `cockpit/sample.py`, `web/index.html`, `web/app.js`, `web/style.css`, `tests/test_api.py`, `README.md`.

**Interface:** `GET /api/status`, `/api/market`, `/api/scanner`, `/api/stocks/{symbol}`, `/api/observations`; `POST /api/observations`; `POST /api/probe`.

- [x] Write failing API integration tests for synthetic labeling, unknown symbols, observation persistence and no credential leak.
- [x] Implement an opt-in Alpaca probe, sample mode and local-only HTTP application.
- [x] Build Today, Scanner, Stock Explorer, contextual Learn and observation interaction with readable dark UI.
- [x] Run entire suite and manually test HTTP and a browser-style fetch.
- [x] Record remaining Stage 0 gaps (feed entitlement, volume semantics, streaming/recovery, real-market soak test) in README.

## Done for this slice

- Application starts with a single documented command, shows an unmistakable example-data banner, and has working screens.
- Tests pass against numeric, persistence and HTTP behavior.
- Credentialed mode never claims full-market coverage or data capability it has not verified.
- The README explicitly distinguishes this first slice from the complete v0.2 MVP.
