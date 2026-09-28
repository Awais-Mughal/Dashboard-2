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
    session = parse_time(available[-1]["t"]).astimezone(NY).date()
    today = [b for b in available if parse_time(b["t"]).astimezone(NY).date() == session and
             (9, 30) <= (parse_time(b["t"]).astimezone(NY).hour, parse_time(b["t"]).astimezone(NY).minute) < (16, 0)]
    if not today:
        return {"symbol": symbol, "status": "unavailable", "feed": feed,
                "cutoff": cutoff.isoformat().replace("+00:00", "Z"),
                "issues": ["no_completed_regular_session_bars"], "change_prev_pct": None,
                "change_open_pct": None, "relative_pp": None, "vwap": None, "volume": None}
    last = today[-1]
    previous = sorted((b for b in bars.get("daily", []) if parse_time(b["t"]).astimezone(NY).date() < session), key=lambda item: item["t"])
    prior = previous[-1] if previous else None
    premarket = [b for b in available if parse_time(b['t']).astimezone(NY).date() == session and
                 (4, 0) <= (parse_time(b['t']).astimezone(NY).hour, parse_time(b['t']).astimezone(NY).minute) < (9, 30)]
    levels = {'premarket_high': max((b['h'] for b in premarket), default=None),
              'premarket_low': min((b['l'] for b in premarket), default=None),
              'previous_high': prior.get('h') if prior else None,
              'previous_low': prior.get('l') if prior else None,
              'previous_close': prior.get('c') if prior else None,
              'session_open': today[0]['o'],
              'five_day_high': max((b['h'] for b in previous[-5:]), default=None) if len(previous) >= 5 else None,
              'five_day_low': min((b['l'] for b in previous[-5:]), default=None) if len(previous) >= 5 else None,
              'twenty_day_high': max((b['h'] for b in previous[-20:]), default=None) if len(previous) >= 20 else None,
              'twenty_day_low': min((b['l'] for b in previous[-20:]), default=None) if len(previous) >= 20 else None}
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
