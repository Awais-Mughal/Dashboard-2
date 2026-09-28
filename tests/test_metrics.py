import unittest

from cockpit.metrics import breadth, compute_snapshot, market_phase


def series(previous_close=100, minute=None):
    minute = minute or [
        {"t": "2026-09-24T13:30:00Z", "o": 102, "h": 103, "l": 101, "c": 102, "v": 100, "vw": 102},
        {"t": "2026-09-24T13:31:00Z", "o": 102, "h": 106, "l": 102, "c": 105, "v": 300, "vw": 104},
    ]
    return {"daily": [{"t": "2026-09-23T04:00:00Z", "o": 99, "h": 103, "l": 98, "c": previous_close, "v": 1000}], "minute": minute}


class MetricTests(unittest.TestCase):
    def test_returns_and_vwap_use_hand_computed_completed_bars(self):
        result = compute_snapshot("AAA", series(), feed="sample", as_of="2026-09-24T13:32:00Z")
        self.assertAlmostEqual(result["change_prev_pct"], 5)
        self.assertAlmostEqual(result["change_open_pct"], 100 * (105 / 102 - 1))
        self.assertEqual(result["vwap"], 103.5)
        self.assertEqual(result["previous_high"], 103)
        self.assertEqual(result["cutoff"], "2026-09-24T13:32:00Z")

    def test_relative_return_is_percentage_points_at_same_cutoff(self):
        peer = series(200, [
            {"t": "2026-09-24T13:30:00Z", "o": 200, "h": 202, "l": 200, "c": 202, "v": 50, "vw": 201},
            {"t": "2026-09-24T13:31:00Z", "o": 202, "h": 203, "l": 202, "c": 202, "v": 50, "vw": 202},
        ])
        result = compute_snapshot("AAA", series(), peer, as_of="2026-09-24T13:32:00Z")
        self.assertAlmostEqual(result["relative_pp"], 4)

    def test_partial_bar_after_cutoff_is_excluded(self):
        result = compute_snapshot("AAA", series(), as_of="2026-09-24T13:31:30Z")
        self.assertEqual(result["last"], 102)
        self.assertEqual(result["volume"], 100)

    def test_missing_volume_disables_vwap_and_volume_total(self):
        data = series()
        data["minute"][1]["v"] = None
        result = compute_snapshot("AAA", data, as_of="2026-09-24T13:32:00Z")
        self.assertIsNone(result["vwap"])
        self.assertIsNone(result["volume"])
        self.assertIn("volume", result["issues"])

    def test_breadth_reports_eligible_denominator_and_missing(self):
        self.assertEqual(breadth([
            {"change_prev_pct": 5, "status": "valid"},
            {"change_prev_pct": -1, "status": "valid"},
            {"change_prev_pct": None, "status": "partial"},
        ]), {"advancing": 1, "declining": 1, "unchanged": 0, "eligible": 2, "configured": 3, "coverage_pct": 66.7})

    def test_stale_benchmark_cannot_produce_current_relative_return(self):
        peer = series()
        peer["minute"] = peer["minute"][:1]
        result = compute_snapshot("AAA", series(), peer, as_of="2026-09-24T13:32:00Z")
        self.assertIsNone(result["relative_pp"])
        self.assertIn("benchmark", result["issues"])

    def test_premarket_only_bars_do_not_masquerade_as_regular_session(self):
        data = series()
        data["minute"] = [{"t": "2026-09-24T12:00:00Z", "o": 101, "h": 102, "l": 100, "c": 101, "v": 100, "vw": 101}]
        result = compute_snapshot("AAA", data, as_of="2026-09-24T12:01:00Z")
        self.assertEqual(result["status"], "unavailable")
        self.assertIsNone(result["change_open_pct"])

    def test_reference_levels_and_feed_gap(self):
        data = series()
        data['minute'].insert(0, {'t': '2026-09-24T12:00:00Z', 'o': 100, 'h': 108, 'l': 95, 'c': 99, 'v': None, 'vw': None})
        result = compute_snapshot('AAA', data, as_of='2026-09-24T13:32:00Z')
        self.assertEqual(result['levels']['premarket_high'], 108)
        self.assertEqual(result['levels']['premarket_low'], 95)
        self.assertEqual(result['levels']['previous_low'], 98)
        self.assertAlmostEqual(result['opening_gap_pct'], 2)

    def test_price_breadth_includes_rows_without_volume(self):
        result = breadth([{'change_prev_pct': 2, 'status': 'partial', 'issues': ['volume']}])
        self.assertEqual(result['eligible'], 1)

    def test_previous_minute_session_overrides_misaligned_daily_candle(self):
        data = {
            'minute': [
                {'t': '2026-09-23T19:58:00Z', 'o': 99, 'h': 100, 'l': 98, 'c': 99, 'v': None, 'vw': None},
                {'t': '2026-09-23T19:59:00Z', 'o': 99, 'h': 101, 'l': 99, 'c': 100, 'v': None, 'vw': None},
                {'t': '2026-09-24T13:30:00Z', 'o': 102, 'h': 103, 'l': 101, 'c': 102, 'v': None, 'vw': None},
                {'t': '2026-09-24T13:31:00Z', 'o': 102, 'h': 106, 'l': 102, 'c': 105, 'v': None, 'vw': None},
            ],
            # eToro can label the current daily candle with the prior UTC date.
            'daily': [{'t': '2026-09-23T00:00:00Z', 'o': 102, 'h': 106, 'l': 101, 'c': 105, 'v': None}],
        }
        result = compute_snapshot('AAA', data, as_of='2026-09-24T13:32:00Z')
        self.assertEqual(result['previous_close'], 100)
        self.assertEqual(result['levels']['previous_high'], 101)
        self.assertAlmostEqual(result['change_prev_pct'], 5)

    def test_price_context_reports_range_position_and_multi_day_returns(self):
        data = series()
        data['daily'] = [
            {'t': f'2026-09-{day:02d}T04:00:00Z', 'o': 80 + day, 'h': 83 + day, 'l': 79 + day, 'c': 81 + day, 'v': None}
            for day in range(1, 21)
        ]
        result = compute_snapshot('AAA', data, as_of='2026-09-24T13:32:00Z')
        self.assertAlmostEqual(result['session_range_position_pct'], 80)
        self.assertIsNotNone(result['return_5d_pct'])
        self.assertIsNotNone(result['return_20d_pct'])
        self.assertIsNotNone(result['atr14'])
        self.assertIsNotNone(result['atr_pct'])

    def test_market_phase_distinguishes_closed_and_regular_hours(self):
        self.assertEqual(market_phase('2026-09-28T09:00:00Z')['phase'], 'premarket')
        self.assertEqual(market_phase('2026-09-28T15:00:00Z')['phase'], 'regular')
        self.assertEqual(market_phase('2026-09-27T15:00:00Z')['phase'], 'market_closed')


if __name__ == "__main__":
    unittest.main()
