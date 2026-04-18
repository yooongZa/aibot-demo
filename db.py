"""Lightweight SQLite logging for consultation analytics.

Three tables:
- sessions: one row per chat (session_id PK, started_at, profile JSON)
- turns: one row per (user, assistant) exchange with stage + detected needs
- feedback: thumbs up/down attached to a turn

All writes are best-effort and wrapped in try/except so logging failures never
break a live consultation. Reads are intended for offline dashboards.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "consultation_logs.sqlite"


SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    user_profile TEXT
);

CREATE TABLE IF NOT EXISTS turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    turn_index INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    stage TEXT NOT NULL,
    user_text TEXT NOT NULL,
    assistant_text TEXT NOT NULL,
    detected_needs TEXT,
    recommended_products TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    turn_id TEXT NOT NULL,
    rating TEXT NOT NULL,
    products TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id);
CREATE INDEX IF NOT EXISTS idx_feedback_session ON feedback(session_id);
"""


@contextmanager
def _connect():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(SCHEMA)


def _now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def log_session_start(session_id: str, user_profile: dict | None) -> None:
    try:
        with _connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sessions (session_id, started_at, user_profile) VALUES (?, ?, ?)",
                (session_id, _now(), json.dumps(user_profile or {}, ensure_ascii=False)),
            )
    except sqlite3.Error:
        pass


def log_turn(
    session_id: str,
    turn_index: int,
    stage: str,
    user_text: str,
    assistant_text: str,
    detected_needs: list[str],
    recommended_products: list[str],
) -> None:
    try:
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO turns
                (session_id, turn_index, created_at, stage, user_text, assistant_text,
                 detected_needs, recommended_products)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    turn_index,
                    _now(),
                    stage,
                    user_text,
                    assistant_text,
                    json.dumps(detected_needs, ensure_ascii=False),
                    json.dumps(recommended_products, ensure_ascii=False),
                ),
            )
    except sqlite3.Error:
        pass


def log_feedback(
    session_id: str, turn_id: str, rating: str, products: list[str]
) -> None:
    try:
        with _connect() as conn:
            conn.execute(
                "INSERT INTO feedback (session_id, turn_id, rating, products, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    session_id,
                    turn_id,
                    rating,
                    json.dumps(products, ensure_ascii=False),
                    _now(),
                ),
            )
    except sqlite3.Error:
        pass


def session_summary(session_id: str) -> dict:
    """Read-side helper used by tests and ad-hoc analytics scripts."""
    with _connect() as conn:
        cur = conn.cursor()
        turn_count = cur.execute(
            "SELECT COUNT(*) FROM turns WHERE session_id = ?", (session_id,)
        ).fetchone()[0]
        last_stage_row = cur.execute(
            "SELECT stage FROM turns WHERE session_id = ? ORDER BY turn_index DESC LIMIT 1",
            (session_id,),
        ).fetchone()
        feedback_rows = cur.execute(
            "SELECT rating, COUNT(*) FROM feedback WHERE session_id = ? GROUP BY rating",
            (session_id,),
        ).fetchall()
        return {
            "turns": turn_count,
            "last_stage": last_stage_row[0] if last_stage_row else None,
            "feedback": dict(feedback_rows),
        }
