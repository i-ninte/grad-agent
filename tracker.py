"""SQLite pipeline tracker: profs, programs, drafts, statuses."""
from __future__ import annotations
import sqlite3, os, json, time
from pathlib import Path

DB = Path(__file__).parent / "db.sqlite"

SCHEMA = """
CREATE TABLE IF NOT EXISTS targets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  prof_name TEXT, prof_email TEXT, university TEXT, program TEXT,
  area TEXT, deadline TEXT, paper_url TEXT, notes TEXT,
  status TEXT DEFAULT 'new',   -- new|drafted|sent|replied|rejected|silent
  created_at INTEGER, updated_at INTEGER
);
CREATE TABLE IF NOT EXISTS drafts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  target_id INTEGER, kind TEXT,   -- email|sop|cv|article
  path TEXT, subject TEXT, created_at INTEGER,
  FOREIGN KEY(target_id) REFERENCES targets(id)
);
"""


def _conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    return c


def add_target(**kw) -> int:
    now = int(time.time())
    fields = ["prof_name", "prof_email", "university", "program", "area",
              "deadline", "paper_url", "notes"]
    vals = [kw.get(f, "") for f in fields]
    with _conn() as c:
        cur = c.execute(
            f"INSERT INTO targets ({','.join(fields)}, created_at, updated_at) "
            f"VALUES ({','.join('?' * len(fields))}, ?, ?)",
            (*vals, now, now),
        )
        return cur.lastrowid


def add_draft(target_id: int, kind: str, path: str, subject: str = "") -> int:
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO drafts (target_id, kind, path, subject, created_at) VALUES (?,?,?,?,?)",
            (target_id, kind, path, subject, int(time.time())),
        )
        c.execute("UPDATE targets SET status='drafted', updated_at=? WHERE id=?",
                  (int(time.time()), target_id))
        return cur.lastrowid


def set_status(target_id: int, status: str) -> None:
    with _conn() as c:
        c.execute("UPDATE targets SET status=?, updated_at=? WHERE id=?",
                  (status, int(time.time()), target_id))


def list_pipeline(status: str | None = None) -> list[dict]:
    q = "SELECT * FROM targets"
    args: tuple = ()
    if status:
        q += " WHERE status=?"; args = (status,)
    q += " ORDER BY updated_at DESC"
    with _conn() as c:
        return [dict(r) for r in c.execute(q, args).fetchall()]
