import json
import sqlite3
from contextlib import contextmanager
from typing import Iterator

from .config import DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS config (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assignments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL,
  type TEXT NOT NULL,
  title TEXT,
  scenario TEXT,
  image_data TEXT,
  focus_dimension TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_assignments_date ON assignments(date);

CREATE TABLE IF NOT EXISTS submissions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  assignment_id INTEGER NOT NULL REFERENCES assignments(id),
  date TEXT NOT NULL,
  content TEXT NOT NULL,
  char_count INTEGER NOT NULL,
  scores TEXT NOT NULL,
  feedback TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_submissions_date ON submissions(date);
CREATE INDEX IF NOT EXISTS idx_submissions_assignment ON submissions(assignment_id);
"""

_ASSIGNMENT_TYPE_MIGRATIONS = {
    "scenario": "daily",
    "image": "image_practice",
}


def init_db() -> None:
    with connect() as conn:
        conn.executescript(_SCHEMA)
        for legacy, target in _ASSIGNMENT_TYPE_MIGRATIONS.items():
            conn.execute("UPDATE assignments SET type = ? WHERE type = ?", (target, legacy))
        conn.commit()


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def get_config(key: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
        return json.loads(row["value"]) if row else None


def set_config(key: str, value: dict) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO config(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, json.dumps(value, ensure_ascii=False)),
        )


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row else None
