import tempfile
import unittest
from pathlib import Path

from cockpit.storage import Store


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "db.sqlite")

    def tearDown(self):
        self.tmp.cleanup()

    def test_bar_upsert_does_not_duplicate(self):
        bar = {"t": "2026-09-24T13:30:00Z", "o": 1, "h": 2, "l": 1, "c": 2, "v": 3, "vw": 1.5}
        self.store.save_bars("AAPL", "alpaca:iex", "1Min", [bar, bar])
        self.assertEqual(self.store.get_bars("AAPL", "alpaca:iex", "1Min"), [bar])

    def test_observation_keeps_original_snapshot(self):
        snapshot = {"symbol": "AAPL", "last": 100, "feed": "sample", "cutoff": "2026-09-24T13:30:00Z"}
        created = self.store.save_observation(snapshot, "Check if above level")
        snapshot["last"] = 200
        self.assertEqual(self.store.list_observations()[0]["snapshot"]["last"], 100)
        self.assertEqual(created["note"], "Check if above level")


if __name__ == "__main__": unittest.main()
