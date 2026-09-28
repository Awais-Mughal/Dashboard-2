"""Local SQLite persistence for the prototype; observations are immutable."""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as db:
            db.executescript("""
              CREATE TABLE IF NOT EXISTS bars (
                symbol TEXT NOT NULL, feed TEXT NOT NULL, timeframe TEXT NOT NULL,
                t TEXT NOT NULL, payload TEXT NOT NULL,
                PRIMARY KEY(symbol, feed, timeframe, t)
              );
              CREATE TABLE IF NOT EXISTS observations (
                id TEXT PRIMARY KEY, created_at TEXT NOT NULL,
                snapshot_json TEXT NOT NULL, note TEXT NOT NULL
              );
              CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, payload TEXT NOT NULL);
            """)

    def _connection(self):
        return sqlite3.connect(self.path, timeout=10)

    def save_bars(self, symbol, feed, timeframe, bars):
        with self._connection() as db:
            db.executemany("INSERT INTO bars VALUES (?, ?, ?, ?, ?) ON CONFLICT(symbol,feed,timeframe,t) DO UPDATE SET payload=excluded.payload", [
                (symbol, feed, timeframe, bar["t"], json.dumps(bar, sort_keys=True)) for bar in bars
            ])

    def get_bars(self, symbol, feed, timeframe, start=None, end=None):
        query = "SELECT payload FROM bars WHERE symbol=? AND feed=? AND timeframe=?"
        args = [symbol, feed, timeframe]
        if start:
            query += " AND t>=?"
            args.append(start)
        if end:
            query += " AND t<?"
            args.append(end)
        query += " ORDER BY t"
        with self._connection() as db:
            return [json.loads(row[0]) for row in db.execute(query, args)]

    def save_observation(self, snapshot, note=""):
        if not isinstance(snapshot, dict) or not snapshot.get("symbol") or not snapshot.get("cutoff"):
            raise ValueError("An observation requires a timestamped snapshot")
        if len(note) > 2000:
            raise ValueError("Observation note too long")
        item = {"id": uuid.uuid4().hex, "created_at": datetime.now(timezone.utc).isoformat(), "snapshot": json.loads(json.dumps(snapshot)), "note": note}
        with self._connection() as db:
            db.execute("INSERT INTO observations VALUES (?, ?, ?, ?)", (item["id"], item["created_at"], json.dumps(item["snapshot"]), note))
        return item

    def list_observations(self):
        with self._connection() as db:
            return [{"id": row[0], "created_at": row[1], "snapshot": json.loads(row[2]), "note": row[3]} for row in db.execute("SELECT id,created_at,snapshot_json,note FROM observations ORDER BY created_at DESC")]

    def setting(self, key, default=None):
        with self._connection() as db:
            row = db.execute('SELECT payload FROM settings WHERE key=?', (key,)).fetchone()
            return json.loads(row[0]) if row else default

    def set_setting(self, key, value):
        with self._connection() as db:
            db.execute('INSERT INTO settings VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET payload=excluded.payload', (key, json.dumps(value)))
