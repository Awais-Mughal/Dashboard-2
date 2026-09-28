# Market Learning Cockpit — Revised MVP Specification

**Version:** 0.2  
**Date:** 25 September 2026  
**Status:** Revised design for review; not an implemented or validated trading system.  
**Basis:** Original v0.1 specification and the accepted developer/trading review.  
**Audience:** One private user learning to interpret US equity markets.

## 1. Product brief

Build a private dashboard that collects market information, calculates transparent metrics, explains observations, and preserves examples for later review. The user should understand market behavior with less manual research and calculation.

The dashboard must help answer:

1. What has changed in the market since I last checked?
2. Which sectors and tracked stocks are unusually active?
3. Is a stock moving with or against its benchmark, and over which interval?
4. Where is price relative to clearly identified historical reference levels?
5. What evidence supports or contradicts an interpretation?
6. What happened after an observation I saved?

Success is better understanding and lower manual effort. Profitability, trading edge, and correct price prediction are not MVP success claims.

### Working assumptions

- US stocks and ETFs only; one private user; existing Ubuntu VPS.
- One-minute analytical updates and completed five-minute event bars are sufficient.
- A reduced universe or delayed mode is acceptable if data limitations are explicit.
- No broker order permissions or execution are needed.
- Monthly paid-data spending is not assumed. Any subscription choice follows a capability test and an explicit cost decision.
- Technical defaults below are initial product conventions, not empirically validated trading rules.

## 2. Scope and release boundaries

| Core MVP | Next release | Deferred |
|---|---|---|
| Today, Scanner, Stock Explorer, contextual Learn | Narrow level/VWAP event engine | Automated trading |
| Watchlist and saved observations | Historical replay interface | Portfolio management |
| Verified metrics and reference levels | Optional on-demand AI explanations | Options flow, Level II, CVD |
| Data status and source provenance | Richer catalyst ingestion | Automatic swing/pattern recognition |
| Basic scheduled-event context | Optional hypothetical trade journal | Full-market scanning |
| Outcome review from stored bars | Larger universe with appropriate feed | Continuous AI narration |

Point-in-time snapshots and event-ready storage begin in the core MVP even though the replay interface is deferred. The core does not depend on AI or advanced pattern labels.

## 3. Data feasibility gate — before feature implementation

Do not designate eToro, Alpaca, or another service as the primary analytical feed solely because an API key exists.

Run a read-only probe on SPY, QQQ, AAPL, and NVDA, plus one appropriate sector/theme benchmark. Collect recent daily history and at least 20 eligible prior sessions of intraday history where entitled. Observe available live regular-session and premarket behavior. A successful authentication call alone does not pass this gate.

| Capability | Evidence required | Consequence if unavailable |
|---|---|---|
| Price meaning | Document whether prices are trades, quotes, midpoint, or derived | Label the series; disable trade-based interpretations when inappropriate |
| Volume meaning | Units, venue coverage, historical/live consistency | Disable RVOL, volume-based VWAP, and turnover if semantics are unknown |
| Quote meaning | Broker, venue, or consolidated scope; quote timestamps | Label scope; do not claim market-wide spread or execution quality |
| Session coverage | Observed coverage compared with documented session availability | Mark premarket levels partial or unavailable |
| Intraday history | Eligible session count, pagination, gaps, rate limits | Show insufficient history; reduce features |
| Stream capacity | Actual subscription acknowledgements and documented limits | Reduce universe or use an entitled delayed mode |
| Recovery | Reconnect, resubscribe, backfill, duplicate delivery | Block live release until tested |
| Corrections | Revised-bar behavior and available revision channels | Document limits and preserve received versions |
| Corporate actions | Split/dividend policy and effective dates | Suppress affected comparisons until aligned |
| Usage rights | Applicable personal display/storage permissions | Keep deployment within permitted use |

### Feed selection rules

- Select one canonical feed per analytical series, with consistent price and volume scope.
- Never splice another feed into an existing volume history silently.
- A second provider is a diagnostic comparison, not automatic ground truth.
- Differences must be compared only after matching instrument, feed scope, interval, session, adjustment, and timestamp.
- Provider failure produces a visible degraded state. Switching feeds requires a new series identity and sufficient compatible history.
- Record the chosen provider, feed, capabilities, limits, and verification date in a configuration record.

### Available modes

| Mode | Behavior |
|---|---|
| Verified live | Current values using a qualified feed |
| Limited live | Restricted venue/universe; scope prominently labeled |
| Delayed study | All related analytics use the same delayed information cutoff |
| Recorded study | Stored observations and historical charts; no live claims |

Current reference: Alpaca documentation checked on 25 September 2026 lists IEX-only real-time equity data and a 30-symbol WebSocket subscription limit for Basic. This is a planning constraint, not a guarantee about the user's account. Verify entitlements at integration time. The original 40–60 stocks plus ETFs cannot be assumed to fit this stream budget.

## 4. Universe and benchmark policy

- Begin with the probe universe; expand only after capacity and quality checks.
- Allocate feed capacity to market and sector benchmarks before adding scanner stocks.
- Maintain separate instrument groups: market ETFs, sector ETFs, theme/industry ETFs, and individual stocks.
- Market references: SPY, QQQ, IWM where available.
- Full sector view, when supported: XLK, XLF, XLE, XLV, XLI, XLY, XLP, XLU, XLB, XLC, XLRE. Show missing groups explicitly.
- SMH is a semiconductor theme/industry benchmark and must not be presented as an additional mutually exclusive sector.
- Map each stock explicitly to a sector benchmark and optionally a theme benchmark. Store mapping versions/effective dates.
- QQQ is a Nasdaq-100 reference, not a synonym for the entire market or technology sector.
- Freeze the tracked-stock universe for each session. Scanner filters must not change the breadth denominator.
- Keep ETFs outside stock breadth; disclose selection bias and sector concentration.
- Do not impose a $500 maximum share price. Initial eligibility can use supported instrument type, data completeness, and documented liquidity screens.
- Any automated average-volume eligibility screen requires verified volume and a stated lookback; unavailable eligibility inputs remain unknown.

## 5. Session and price conventions

- Store timestamps in UTC; assign sessions using `America/New_York` and an exchange calendar.
- Display exchange time and optionally user-local time. Never hard-code a UTC offset.
- Respect holidays and early closes. Regular session is the exchange-calendar interval, normally 09:30–16:00 ET.
- Premarket analysis window defaults to 04:00 ET up to the regular-session open; actual feed coverage must be disclosed.
- After-hours data is kept separate and only displayed within verified coverage.
- Handle official auction prints according to feed trade-condition rules. Do not drop the official close merely because it is timestamped at the session boundary.
- A bar timestamp denotes interval start. Store interval end and receipt time separately.
- Five-minute intervals are anchored at the regular-session open.
- Live partial candles may be charted with an explicit label; calculations and event confirmations use completed intervals.
- Completed bars may later be revised; completion is not a claim of immutability.
- Previous session means previous exchange trading session, not previous calendar day.
- Use split-consistent prices/volumes for cross-session analysis and raw current prices for display. Do not silently use total-return-adjusted history for displayed price levels. Flag ex-dividend effects separately.
- A split or unresolved corporate action blocks affected metrics until the normalization is verified.

## 6. Metric contract

Each computed result contains value, unit, instrument, session, information cutoff, calculation time, source series, input coverage, method/version, status, and reason when unavailable.

Statuses: `valid`, `provisional`, `partial`, `stale`, `insufficient_history`, `unavailable`.

Unknown values are null, never zero. Do not substitute stale inputs without labeling them.

### 6.1 Returns and relative performance

| Metric | Definition |
|---|---|
| Change since prior close | `100 × (P(t) / C_prev − 1)` using the selected comparable close |
| Return since open | `100 × (P(t) / O_session − 1)` |
| Premarket change | Same prior-close formula using a timestamped eligible premarket trade; unavailable when no suitable trade exists |
| Opening gap | `100 × (O_session / C_prev − 1)`; freezes once the opening reference is established |
| Benchmark-relative return | `stock_return − benchmark_return`, measured in percentage points |

Store `open_method` and `close_method`. Use the label “official opening gap” only when the opening reference is verified as official. Otherwise label “feed opening gap.” Never describe a quote-derived estimate as an observed opening trade.

Relative returns must share the same return horizon, session, and information cutoff. Expose prior-close and since-open comparisons independently. Do not call a stock's opening gap “intraday strengthening.” Defer automatic strengthening/weakening labels until a specific trailing interval and threshold are defined and evaluated.

### 6.2 Volume, turnover, and VWAP

- Exact traded dollar volume for a covered trade set: `sum(trade_price × trade_size)`.
- With verified bar VWAP: aggregate `sum(bar_vwap × bar_volume)` over compatible bars.
- With OHLCV only: HLC3-weighted turnover is an approximation and must be labeled as such.
- `latest_price × cumulative_volume` is not the exact historical traded value.
- Regular-session VWAP resets at the session open and uses only eligible regular-session inputs.
- Aggregate verified bar VWAP as `sum(bar_vwap × bar_volume) / sum(bar_volume)`; disclose feed coverage and trade eligibility.
- If only OHLCV exists, `sum(HLC3 × volume) / sum(volume)` is labeled “bar-estimated VWAP.”
- Zero total eligible volume yields unavailable VWAP.
- Premarket volume is separate from regular-session volume. Do not mix their reset boundaries.

### 6.3 Same-time RVOL

Default baseline: previous 20 eligible trading sessions with the same feed, adjustment convention, and session window. Exclude shortened sessions from the initial regular-session baseline. Show actual eligible count and excluded-session reasons.

- Bar RVOL: completed five-minute volume divided by mean volume for the identical five-minute interval across baseline sessions.
- Cumulative RVOL: volume from session open through the latest completed minute divided by mean cumulative volume through the identical cutoff across baseline sessions.
- Minimum baseline for an active RVOL value: 20 eligible observations; otherwise `insufficient_history`.
- Never compare a partial interval with complete historical intervals.
- A verified no-trade interval can contribute zero volume; a missing interval cannot.
- Zero baseline volume yields unavailable RVOL, not infinity.
- Premarket RVOL is deferred; premarket volume may be shown if verified.
- Thresholds 1.5×, 2×, and 3× are descriptive UI bands, not evidence of profitable setups.

### 6.4 ATR and distance

Daily true range: `max(H − L, abs(H − C_prev), abs(L − C_prev))`.

ATR(14) uses Wilder smoothing on completed regular-session daily bars. Seed with the arithmetic mean of the first 14 true ranges; apply `(13 × previous_ATR + current_TR) / 14` thereafter. Record history start and adjustment policy; require at least 100 completed daily bars for the default production warmup. The same initialization must be used in live calculations and recorded study.

- ATR%: `100 × previous_completed_session_ATR / current_price`.
- Signed level distance: `level_price − current_price`.
- Percentage distance: `100 × signed_distance / current_price`.
- ATR distance: `signed_distance / previous_completed_session_ATR`.
- Range/ATR describes range size; it does not impose a ceiling on further movement.
- Display distance rather than attaching a universal “danger” rule to 0.5%.

### 6.5 Spread and liquidity

`spread = ask − bid`; `mid = (ask + bid) / 2`; `spread_pct = 100 × spread / mid`.

Require positive, valid bid/ask from an eligible quote. Crossed or stale quotes are flagged and excluded from spread interpretation. A locked quote is labeled rather than treated as evidence of exceptional liquidity.

Label quote scope. Spread and turnover do not establish available depth, fill certainty, or slippage. No “good liquidity” claim based only on a narrow spread.

### 6.6 Reference levels

| Level | Definition and availability |
|---|---|
| PMH/PML | High/low of eligible premarket trades; developing until open, then frozen |
| PDH/PDL | High/low of previous completed regular session |
| Previous close | Explicit method and split-consistent price |
| Session open | Explicit method; not assumed to be the auction |
| 5-session high/low | Prior five completed regular sessions, excluding today |
| 20-session high/low | Prior twenty completed regular sessions, excluding today |
| Opening range | First 15 regular-session minutes; developing until 09:45 ET on a normal open |

Store each level's type, creation time, information cutoff, price, coverage, and method. Freeze the opening range after its window completes. Partial premarket coverage produces a partial-level label and disables default PMH/PML event alerts.

“Nearest tracked level above/below price” searches only known eligible reference levels. Merge coincident display labels while retaining their identities. No level above price means “none in tracked set,” not “no resistance.” Support/resistance interpretations remain hypotheses.

### 6.7 Tracked-universe breadth

- Count individual stocks only, from the session's frozen universe.
- Advancing/declining/unchanged compares price with its comparable prior close using unrounded values represented at validated price precision.
- Exclude stale, missing, or invalid inputs. Show `eligible / configured` and all exclusions.
- Above-VWAP breadth has its own eligible denominator because volume availability may differ.
- Default: suppress aggregate interpretation below 90% input coverage; show counts and a low-coverage notice.
- Display the universe definition and sector concentration. Never relabel this as exchange-wide breadth solely because the feed is consolidated.

## 7. Screens and interaction

### Today

Show session/mode status, data cutoff, benchmark performance since close and since open, tracked breadth, sector comparison, upcoming scheduled events, and three to five notable changes since the user's previous visit.

Market summaries use factual clauses, for example: “QQQ is above its regular-session VWAP; IWM is below it; 32 of 50 eligible tracked stocks are above their prior close.” Do not force a bullish/bearish regime label.

### Scanner

Default columns: symbol, change since open, cumulative RVOL, relative return versus selected benchmark, and nearest tracked level distance. Additional columns are optional.

- Separate activity, direction, location, data quality, and caution badges.
- No composite weighted attention score.
- Sort by a named observable metric; explain the active sort.
- Allow pause/resume of reordering while values continue updating visibly.
- Support watchlist-only view, filter reset, and metric explanations.
- Retain unavailable rows with reasons; do not silently rank nulls as zeros.
- High activity and caution can coexist.

### Stock Explorer

Daily context and intraday chart; session shading; VWAP/estimate; reference levels; return horizons; volume context; observed facts; a possible interpretation; contrary evidence; and Save Observation.

Use progressive disclosure. Source freshness stays visible; internal implementation details belong in an expandable calculation panel.

### Learn

Every core metric has definition, formula, simple numerical example, source scope, calculation convention, limitations, and common mistakes. Link the explanation to the current metric and saved examples. Include percentage points versus percent, partial bars, missing data, and feed coverage.

Do not require completion of lessons or quizzes to use the application.

### Accessibility and attention

- Dark theme, clear hierarchy, readable type, keyboard access, and text labels alongside colors.
- Watchlist-only notifications by default; quiet mode and rate limiting.
- “No notable change” is a normal result.
- Distinguish live, delayed, recorded, stale, and market-closed states prominently.

## 8. Scheduled events and catalyst context

MVP event context is a small sourced calendar of earnings and major scheduled economic releases. The acquisition method is selected in the data feasibility stage; an imported, timestamped calendar is an acceptable initial fallback.

Store event type, affected symbols, scheduled timestamp or time uncertainty, timezone, source URL, retrieval time, and status. Unknown earnings time is not interpreted as before-market or after-market. A stale/unavailable calendar must not imply “no events.”

Optional catalyst links show headline, publisher, publication time, retrieval time, and related instrument. Do not infer that a headline caused a move merely because the timestamps are nearby. Automatic broad news aggregation and AI causal interpretation are deferred.

## 9. Observation and outcome review

One action saves an immutable observation containing the selected chart window, references to bar revisions, current metrics, levels, source information, and snapshot ID. User input is optional: expectation, contrary evidence/invalidation, and confidence.

Outcome windows: 15 minutes, 60 minutes, and regular-session close. Use only available eligible bars; windows crossing the close are marked truncated rather than extended into the next session automatically.

Report signed price return, highest/lowest observed price after the observation, benchmark-relative return, and relevant data gaps. Exclude the pre-observation portion of an overlapping bar; default evaluation starts with the next full minute.

- Treat these as observations, not simulated fills or trade P/L.
- Do not compute R multiples without an explicitly recorded hypothetical entry and initial risk.
- Original evidence is immutable. Later corrected-data outcomes may be shown separately.
- No “correct regime 73%” scoring without a defined, independently assessable rubric.
- Do not label an action a mistake merely because price later moved against it.
- Capture ordinary and failed examples as well as dramatic winners.

## 10. Limited event engine — next release

The core release stores observations without requiring automatic pattern detection. The following is the bounded extension contract, not a prerequisite for the core dashboard.

Initial event types: level crossed by a completed one-minute close; first five-minute close beyond a frozen level; return into a tolerance band; five-minute close back across the level. VWAP side changes use completed five-minute closes and an explicitly moving reference.

Each rule stores timeframe, reference identity, tolerance, required input quality, state transitions, reset condition, expiry, deduplication key, and rule version. No event type is enabled with an unspecified parameter.

Starting reference-level convention: tolerance `max(validated_price_increment, 0.02 × prior_daily_ATR)`. This is a configurable engineering default requiring evaluation; it is not a validated trading threshold. If ATR or price increment is unavailable, disable the rule.

For an upward level sequence:

1. A completed one-minute close moves from at/below L to above L: record “close crossed above.”
2. A completed five-minute close exceeds L plus tolerance: record the observable close; do not call it acceptance.
3. A subsequent completed five-minute bar overlaps the tolerance band: record “returned to level area.” If it closes below L minus tolerance, record “closed back below.”
4. Never infer an intrabar break/retest order when one bar spans multiple boundaries. Mark the sequence ambiguous.
5. Expire the sequence after 60 minutes or session close, whichever occurs first. A new upward sequence requires a completed five-minute close below L minus tolerance and a 10-minute cooldown.

Downward rules are symmetric. Events are descriptive, not buy/sell instructions. Moving-VWAP rules use the VWAP value at each bar's cutoff and are evaluated independently of frozen-level sequences.

Apply a default notification cap of three per symbol per 15 minutes, coalesce related reference levels, and retain suppressed events in history. Do not interpret a lack of events as lack of activity when inputs are degraded.

Backfill events are labeled historical and never pushed as fresh alerts. Corrections create explicit superseding/retraction records rather than silently rewriting delivered event history.

## 11. Explanation policy

Core explanations are deterministic templates built from the same snapshot as the UI.

Every interpretation follows:

1. **Observed:** A specific fact with horizon and timestamp.
2. **Possible meaning:** A restrained interpretation, when useful.
3. **Contrary evidence:** What already conflicts or would weaken the interpretation.
4. **Next observation:** A measurable behavior to watch, not an order.

No invented catalysts, institutional positioning claims from volume alone, guaranteed patterns, unsupported probabilities, or implied execution prices.

Optional AI later receives already-computed facts, metric definitions, quality flags, source references, and an information cutoff. It cannot modify calculations or authoritative event state. Validate output shape, reference provenance, numeric consistency, and expiry. Cache by snapshot/rule/prompt version; use a configurable daily budget and deterministic fallback. Treat external news text as untrusted content, never as instructions.

## 12. Architecture and technology

One repository, one backend codebase, one database. Separate processes by responsibility without introducing microservices infrastructure.

| Component | Role |
|---|---|
| Dedicated Python worker | Ingestion, backfill, normalization, incremental metrics, scheduled outcomes |
| PostgreSQL | Bars/revisions, snapshots, levels, observations, configuration, event records |
| FastAPI | Authenticated read/write API and browser updates |
| React/Next.js with TypeScript | Private dashboard and interactions |
| One chart library | Candles, volume, reference overlays; choose after a small chart test |
| Caddy or Nginx | HTTPS and routing |
| Docker Compose | Worker, API, frontend, database, proxy lifecycle |

- Only one active ingestion worker owns provider subscriptions initially. Multiple API workers must not start ingestion.
- Prefer verified provider minute bars, then aggregate five-minute bars locally. Never infer executed volume from quote updates.
- Use Pandas for batch/backfill work where helpful; incremental live calculations should not reload all history each minute.
- PostgreSQL is accessed through the backend, never directly by the browser.
- No Redis, Kafka, Kubernetes, or tick warehouse in the MVP.
- Choose either SSE or browser WebSocket for updates; default SSE with REST actions is sufficient for one-way snapshot notifications. Provider WebSockets remain independent.
- Pin dependencies and schema migrations; maintain separate development and production credentials.

## 13. Provider and internal contracts

Provider adapter responsibilities: list/resolve instruments; report capabilities; fetch paginated bars with explicit feed/session/adjustment; fetch eligible quotes; subscribe to supported channels; normalize timestamps; surface revisions, rate limits, and disconnects.

Unsupported operations return an explicit capability error. They must not synthesize missing volume, claim unavailable session coverage, or fall back to another feed invisibly.

Bar and quote contracts retain provider-native identifiers where available. Instrument identity is not just the displayed ticker; symbol mappings can change over time.

Every analysis batch receives one information cutoff and snapshot ID. All market/sector/stock comparisons in that batch use compatible completed data through that cutoff. Newer quotes may be shown separately with their own timestamp and must not silently enter older metric snapshots.

## 14. Data model

| Entity | Minimum purpose/key fields |
|---|---|
| instruments | Internal ID, asset type, currency, exchange, price increment, active dates |
| provider_symbols | Instrument, provider/feed, external ID, validity dates |
| universe_memberships | Session, instrument, group, mapping version |
| data_series | Provider, feed, timeframe, session scope, adjustment convention |
| bar_revisions | Series, instrument, interval start/end, OHLCV, bar VWAP, receipt time, revision, quality |
| latest_quotes | Instrument/feed, bid/ask/last with distinct timestamps and quote scope |
| metric_snapshots | Snapshot ID, cutoff, values, method version, quality, input revision references |
| reference_levels | Instrument/session, type, value, created/known time, method, coverage |
| observations | Immutable snapshot, chart context, user notes, expectation, saved time |
| observation_outcomes | Observation, horizon, effective interval, results, data quality/version |
| calendar_events | Type, symbols, schedule, uncertainty, source, retrieval time |
| watchlist | User, instrument, creation time, notes |
| event_records | Rule/version, reference, state, occurred/known/emitted times, supersession |
| ingestion_status | Feed, last receipt, heartbeat, gap ranges, retry/backfill status |

Use unique constraints on normalized bar identity plus revision; repeated identical delivery is a no-op. Index instrument/series/time queries. Use migrations and transactions when publishing related snapshots.

Store `occurred_at` and `known_at` separately. Point-in-time reconstruction selects only versions known by the historical cutoff. Latest corrected bars are a separate research view. Re-running current code against revised history does not recreate the original live experience.

### Retention defaults

- Retain normalized minute bars, revisions, and metric snapshots for 12 months initially, subject to applicable rights and storage measurements.
- Pin all data needed to reconstruct saved observations for as long as the observation is retained, within permitted rights.
- Keep only latest quotes plus bounded diagnostic samples; no unlimited quote history.
- Keep daily aggregates for longer-term chart context where permitted.
- Document deletion/export behavior and monitor disk usage. Revisit retention based on measured growth.

## 15. API surface

Authenticated REST endpoints:

| Endpoint | Purpose |
|---|---|
| `GET /api/status` | Session, mode, feed health, coverage |
| `GET /api/market/summary` | Benchmark and breadth snapshot |
| `GET /api/sectors` | Sector/theme comparisons with horizons |
| `GET /api/scanner` | Filtered/sorted observations with quality |
| `GET /api/stocks/{symbol}` | Explorer snapshot |
| `GET /api/stocks/{symbol}/bars` | Bounded bar window and revision view |
| `GET /api/stocks/{symbol}/levels` | Reference levels and provenance |
| `GET /api/calendar` | Sourced event context and coverage |
| `GET/POST /api/watchlist` | Read/add watchlist items |
| `DELETE /api/watchlist/{instrument_id}` | Remove an item |
| `GET/POST /api/observations` | List/save observations |
| `GET /api/observations/{id}` | Original evidence and outcomes |
| `GET /api/learn/{concept}` | Metric definition and examples |
| `GET /api/updates` | SSE notifications of new snapshots |

All market responses include information cutoff, mode, quality, and snapshot ID. Bound query windows and pagination. Use idempotency keys on observation creation. Validate instrument identifiers, filter fields, sort keys, and user text. Restrict cross-origin access to the private frontend.

## 16. Update and failure behavior

| Item | Default cadence |
|---|---|
| Quotes | Provider event-driven; browser updates throttled |
| One-minute metrics | After completed bar batch or relevant revision |
| Five-minute bar RVOL | After completed five-minute interval |
| Scanner/breadth/sectors | One coherent snapshot per completed minute |
| Frozen daily reference levels | Before session; update only for documented corrections |
| Premarket levels | Developing each minute until open |
| Calendar | At session preparation and according to selected source limits |
| Outcomes | When each saved-observation horizon becomes evaluable |

During a covered active session, a missing expected minute bar triggers a data-gap warning after 90 seconds beyond its interval end. This is an operational default, not proof of a halt. Quote freshness uses a provider-specific configured age threshold; do not infer a feed outage from a quiet symbol alone. Track transport heartbeat separately from market activity.

- Reconnect with bounded exponential backoff and jitter; respect rate limits.
- Backfill from a persisted checkpoint with a small overlap, then deduplicate.
- Mark analytics partial while required intervals are missing; suppress dependent explanations/events.
- Publish corrections atomically and retain revision provenance.
- Confirmed halts require a suitable status source; otherwise say data unavailable/stale.
- Restore worker state and event deduplication state after restart.
- A closed exchange session is a normal state, not a data error.

## 17. Security, operations, and cost

- Private authenticated access over HTTPS; no public anonymous dashboard.
- Provider credentials remain server-side, outside git and browser bundles. Redact secrets from logs.
- Request only needed read permissions where supported. Do not implement order endpoints.
- Database is not publicly exposed; apply least-privilege service accounts.
- Back up durable data daily to protected storage and test restore before release.
- Monitor worker health, stream lag, data gaps, API errors, disk use, and backup age.
- Record monthly VPS, data, backup, and optional AI costs separately. Do not assume a subscription is approved.
- Prepare a short operator guide: start/stop, restart, inspect health, rotate credentials, restore backup, and recover a stream gap.

## 18. Verification and release gates

| Test area | Required evidence |
|---|---|
| Mathematics | Hand-checkable fixtures for returns, percentage-point RS, turnover, VWAP, RVOL, Wilder ATR, spread, levels, breadth |
| Time | Holiday, early-close, DST, session boundary, auction handling, opening-range freeze |
| Integrity | Duplicate deliveries, missing/zero-volume distinction, late bars, corrections, symbol mapping, splits |
| Recovery | Disconnect/backfill, rate limiting, worker restart, browser reconnect, no duplicate observations/alerts |
| Consistency | Same inputs/configuration produce same outputs; related UI panels share snapshot cutoff |
| Point-in-time | Future bars and later revisions do not leak into original observations or replay |
| Degradation | Stale benchmarks disable RS interpretation; incomplete volume disables dependent metrics |
| Security | Authentication enforced, secrets absent from frontend/logs, database private |
| Operations | Backup restore and at least one full regular-session soak test |
| Usability | User can identify market changes, inspect evidence, and save an observation without manual calculations |

Release targets, measured for the configured universe:

- Publish 95% of eligible minute snapshots within 10 seconds of receipt of all required inputs. Measure market-to-provider delay separately.
- Display missing/stale inputs rather than waiting indefinitely for an apparently complete snapshot.
- No unexplained gaps or duplicate records in the session soak test; all exclusions are inspectable.
- Do not claim statistical trading edge from engineering tests or visual examples.

## 19. Implementation sequence

| Stage | Deliverable | Exit criterion |
|---|---|---|
| 0 | Provider feasibility record and budget options | Capabilities, volume semantics, history, rights, and limits established |
| 1 | One stock plus benchmark, chart, core metrics, tooltips | Values traceable to source inputs |
| 2 | Worker/storage/recovery/calendar conventions | Integrity and failure fixtures pass |
| 3 | Today, Scanner, Explorer, watchlist | Coherent snapshots and visible quality states |
| 4 | Contextual Learn, calendar context, observation/outcome review | Complete learning loop works |
| Core release | Private VPS deployment and operator guide | Release gates pass |
| Next release | Limited event engine | Explicit versioned rules and evaluated alert burden |
| Later | Replay UI and optional AI | Point-in-time fidelity and grounded output verified |

Stages are dependency boundaries, not estimated delivery dates. Avoid building every backend metric before testing one end-to-end user flow.

## 20. Changes from v0.1

| Action | Change |
|---|---|
| Keep | Learning purpose, four screens, deterministic calculations, provider abstraction, simple stack |
| Modify | Data strategy becomes capability-led; formulas gain explicit conventions and quality states |
| Remove | Unsupported attention weights, automatic learning-accuracy percentages, unconditional free-data promise |
| Replace | Confident acceptance/resistance labels with observable facts and qualified interpretations |
| Add | Worker separation, provenance/revisions, session calendar, failure behavior, security, acceptance tests |
| Move earlier | Saved observations, contrary evidence, scheduled-event context, point-in-time capture |
| Move later | Complex pattern engine, automatic swing recognition, continuous AI commentary |

## 21. References and unresolved external dependencies

Documentation checked during the review on 25 September 2026:

- Alpaca market-data plans and coverage: https://docs.alpaca.markets/us/docs/about-market-data-api
- Alpaca stock stream, bar VWAP, updated bars, and correction channels: https://docs.alpaca.markets/us/docs/real-time-stock-pricing-data
- eToro official API documentation index: https://api-portal.etoro.com/llms.txt

These sources support provider capability checks, not trading edge. The review did not authenticate to the user's accounts or validate real payloads. Provider selection, applicable entitlements, eToro volume semantics, calendar acquisition, and any paid subscription remain explicit Stage 0 decisions. No feature may silently treat an unresolved dependency as verified.
