# Provider and Core MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing cockpit with a selectable read-only eToro feed and the core user workflows in the v0.2 specification.

**Architecture:** Keep provider normalization server-side and identify each series by feed. Persist personal settings and historical bars in SQLite. Compute outcomes from bars after an immutable observation snapshot, then expose all results through the existing HTTP API and dashboard.

**Tech Stack:** Python standard library, SQLite, vanilla JavaScript.

**Spec:** `market_learning_cockpit_mvp_v0_2.md`.

## Global Constraints

- US stocks and ETFs only; one private user.
- Do not place orders or collect broker write credentials.
- Unknown volume is null, and feeds are not silently spliced.
- Synthetic, recorded, delayed, and stale data require visible provenance.

## Review Focus

- eToro lookup response uses `results` and may contain nonmatching symbols: exact match required.
- eToro candle example has zero volume: do not produce VWAP/RVOL.
- Missing minutes in outcomes: mark partial, never claim a complete window.
- Provider failure: preserve the previous dataset and display the error.
- Online deployment without application auth: integrate only behind authenticated HTTPS service.

## Tasks

### Task 1: Provider adapter

**Files:** `cockpit/etoro.py`, `tests/test_etoro.py`.

- [x] Test exact symbol lookup, headers and unknown volume; confirm failure.
- [x] Implement read-only eToro lookup and candle normalization.
- [x] Confirm tests pass.

### Task 2: Data and metric contracts

**Files:** `cockpit/metrics.py`, `cockpit/storage.py`, `tests/test_metrics.py`.

- [x] Test missing-volume breadth and reference levels; confirm failure.
- [x] Implement reference levels, opening gap, eligible price breadth and settings storage.
- [x] Confirm tests pass.

### Task 3: User workflows and recorded refresh

**Files:** `cockpit/server.py`, `tests/test_api.py`, `web/app.js`, `web/style.css`.

- [x] Test provider selection, watchlist, imported events, outcome windows and failure retention; confirm failure.
- [x] Implement endpoints, recorded two-minute refresh and dashboard controls.
- [x] Confirm API tests and JavaScript syntax pass.

### Task 4: Account and deployment verification

**Files:** deployment repository and secrets configuration (not present in this checkout).

- [ ] Link the actual online project repository or deployment source.
- [ ] Test eToro with a real read-only key; inspect price, sessions, quote and volume semantics.
- [ ] Add authenticated HTTPS hosting, backup/restore, exchange calendar and split-safe history.
- [ ] Validate live streaming/recovery before claiming a live dashboard.
