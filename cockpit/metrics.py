"""Deterministic calculations on normalized minute and daily bars."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")


def parse_time(value):
    if isinstance(value, datetime):
        result = value
    else:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Market timestamps must have a timezone")
    return result.astimezone(timezone.utc)


def market_phase(now=None):
    """Return the simple US equity session phase for display/freshness rules."""
    moment = parse_time(now or datetime.now(timezone.utc)).astimezone(NY)
    clock = (moment.hour, moment.minute)
    if moment.weekday() >= 5:
        phase = "market_closed"
    elif (4, 0) <= clock < (9, 30):
        phase = "premarket"
    elif (9, 30) <= clock < (16, 0):
        phase = "regular"
    elif (16, 0) <= clock < (20, 0):
        phase = "after_hours"
    else:
        phase = "market_closed"
    return {"phase": phase, "exchange_time": moment.isoformat(), "timezone": "America/New_York"}


def _regular_sessions(bars):
    sessions = {}
    for bar in bars:
        local = parse_time(bar["t"]).astimezone(NY)
        if (9, 30) <= (local.hour, local.minute) < (16, 0):
            sessions.setdefault(local.date(), []).append(bar)
    return {day: sorted(items, key=lambda item: item["t"]) for day, items in sessions.items()}


def _daily_context(daily, current_last, session_high, session_low):
    history = sorted(daily, key=lambda item: item["t"])
    # Some broker daily candles are labelled by the UTC day on which the
    # session started. Avoid treating a candle matching today's complete range
    # as the previous day.
    if history:
        latest = history[-1]
        if (abs(float(latest.get("c", 0)) - current_last) < 1e-8 and
                latest.get("h", float("-inf")) >= session_high and
                latest.get("l", float("inf")) <= session_low):
            history = history[:-1]
    closes = [bar.get("c") for bar in history if bar.get("c") and bar.get("c") > 0]
    return_5d = 100 * (current_last / closes[-5] - 1) if len(closes) >= 5 else None
    return_20d = 100 * (current_last / closes[-20] - 1) if len(closes) >= 20 else None
    true_ranges = []
    for index in range(1, len(history)):
        bar, prior_close = history[index], history[index - 1].get("c")
        if prior_close and all(bar.get(key) is not None for key in ("h", "l")):
            true_ranges.append(max(bar["h"] - bar["l"], abs(bar["h"] - prior_close), abs(bar["l"] - prior_close)))
    atr14 = sum(true_ranges[-14:]) / 14 if len(true_ranges) >= 14 else None
    return history, return_5d, return_20d, atr14


def compute_snapshot(symbol, bars, benchmark_bars=None, feed="sample", as_of=None):
    """Return a time-bounded factual snapshot; missing inputs stay null."""
    all_minutes = sorted(bars.get("minute", []), key=lambda item: item["t"])
    if as_of is None:
        if not all_minutes:
            raise ValueError("No minute bars")
        cutoff = parse_time(all_minutes[-1]["t"]) + timedelta(minutes=1)
    else:
        cutoff = parse_time(as_of)
    available = [b for b in all_minutes if parse_time(b["t"]) + timedelta(minutes=1) <= cutoff]
    if not available:
        return {"symbol": symbol, "status": "unavailable", "feed": feed, "cutoff": cutoff.isoformat().replace("+00:00", "Z"), "issues": ["no_completed_bars"], "change_prev_pct": None}
    sessions = _regular_sessions(available)
    session = max(sessions) if sessions else None
    today = sessions.get(session, []) if session else []
    if not today:
        return {"symbol": symbol, "status": "unavailable", "feed": feed,
                "cutoff": cutoff.isoformat().replace("+00:00", "Z"),
                "issues": ["no_completed_regular_session_bars"], "change_prev_pct": None,
                "change_open_pct": None, "relative_pp": None, "vwap": None, "volume": None}
    last = today[-1]
    previous_dates = sorted(day for day in sessions if day < session)
    prior_minutes = sessions[previous_dates[-1]] if previous_dates else []
    previous_daily = sorted((b for b in bars.get("daily", []) if parse_time(b["t"]).astimezone(NY).date() < session), key=lambda item: item["t"])
    prior = ({"c": prior_minutes[-1]["c"], "h": max(b["h"] for b in prior_minutes),
              "l": min(b["l"] for b in prior_minutes), "source": "minute_session"}
             if prior_minutes else (previous_daily[-1] if previous_daily else None))
    premarket = [b for b in available if parse_time(b['t']).astimezone(NY).date() == session and
                 (4, 0) <= (parse_time(b['t']).astimezone(NY).hour, parse_time(b['t']).astimezone(NY).minute) < (9, 30)]
    levels = {'premarket_high': max((b['h'] for b in premarket), default=None),
              'premarket_low': min((b['l'] for b in premarket), default=None),
              'previous_high': prior.get('h') if prior else None,
              'previous_low': prior.get('l') if prior else None,
              'previous_close': prior.get('c') if prior else None,
              'session_open': today[0]['o'],
              'five_day_high': None, 'five_day_low': None,
              'twenty_day_high': None, 'twenty_day_low': None}
    close = prior.get("c") if prior else None
    issues = []
    if close is None or close <= 0:
        issues.append("previous_close")
    volume_ok = all(b.get("v") is not None and b["v"] >= 0 and b.get("vw") is not None for b in today)
    if not volume_ok:
        issues.append("volume")
    volume = sum(b["v"] for b in today) if volume_ok else None
    vwap = sum(b["vw"] * b["v"] for b in today) / volume if volume_ok and volume else None
    if volume_ok and not volume:
        issues.append("zero_volume")
    change_prev = 100 * (last["c"] / close - 1) if close else None
    opening = today[0]["o"]
    change_open = 100 * (last["c"] / opening - 1) if opening else None
    session_high, session_low = max(b["h"] for b in today), min(b["l"] for b in today)
    daily_history, return_5d, return_20d, atr14 = _daily_context(
        bars.get("daily", []), last["c"], session_high, session_low)
    if len(daily_history) >= 5:
        levels['five_day_high'] = max(b['h'] for b in daily_history[-5:])
        levels['five_day_low'] = min(b['l'] for b in daily_history[-5:])
    if len(daily_history) >= 20:
        levels['twenty_day_high'] = max(b['h'] for b in daily_history[-20:])
        levels['twenty_day_low'] = min(b['l'] for b in daily_history[-20:])
    session_range = session_high - session_low
    known_levels = [(name, price) for name, price in levels.items()
                    if price is not None and name != 'session_open']
    above = min(((name, price) for name, price in known_levels if price > last['c']),
                key=lambda item: item[1], default=None)
    below = max(((name, price) for name, price in known_levels if price < last['c']),
                key=lambda item: item[1], default=None)
    level_context = {
        'above': ({'name': above[0], 'price': above[1],
                   'distance_pct': 100 * (above[1] / last['c'] - 1)} if above else None),
        'below': ({'name': below[0], 'price': below[1],
                   'distance_pct': 100 * (below[1] / last['c'] - 1)} if below else None),
    }
    relative = None
    if benchmark_bars is not None:
        other = compute_snapshot("benchmark", benchmark_bars, feed=feed, as_of=cutoff)
        if (other.get("change_prev_pct") is not None and change_prev is not None and
                other.get("bar_end") == (parse_time(last["t"]) + timedelta(minutes=1)).isoformat().replace("+00:00", "Z")):
            relative = change_prev - other["change_prev_pct"]
        else:
            issues.append("benchmark")
    return {
        "symbol": symbol, "feed": feed, "session": str(session),
        "cutoff": cutoff.isoformat().replace("+00:00", "Z"),
        "bar_end": (parse_time(last["t"]) + timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
        "last": last["c"], "open": opening, "previous_close": close,
        "levels": levels, "opening_gap_pct": 100 * (opening / close - 1) if close else None,
        "session_high": session_high, "session_low": session_low,
        "session_range_position_pct": 100 * (last["c"] - session_low) / session_range if session_range else None,
        "return_5d_pct": return_5d, "return_20d_pct": return_20d,
        "atr14": atr14, "atr_pct": 100 * atr14 / last["c"] if atr14 else None,
        "nearest_levels": level_context,
        "previous_close_source": prior.get("source", "daily") if prior else None,
        "previous_high": prior.get("h") if prior else None,
        "change_prev_pct": change_prev, "change_open_pct": change_open,
        "relative_pp": relative, "vwap": vwap, "volume": volume,
        "status": "partial" if issues else "valid", "issues": issues,
        "rvol": None, "rvol_status": "insufficient_history",
    }


def breadth(snapshots):
    eligible = [s for s in snapshots if s.get("change_prev_pct") is not None and s.get("status") in ("valid", "partial") and
                not any(issue in s.get('issues', []) for issue in ('previous_close', 'no_completed_bars', 'no_completed_regular_session_bars'))]
    count = len(snapshots)
    return {
        "advancing": sum(s["change_prev_pct"] > 0 for s in eligible),
        "declining": sum(s["change_prev_pct"] < 0 for s in eligible),
        "unchanged": sum(s["change_prev_pct"] == 0 for s in eligible),
        "eligible": len(eligible), "configured": count,
        "coverage_pct": round(100 * len(eligible) / count, 1) if count else 0,
    }
