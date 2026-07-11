import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_DB_PATH = Path(__file__).resolve().parent.parent.parent / "assistant.sqlite"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS preferences (
                user_id TEXT PRIMARY KEY,
                priority_rules TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                notes TEXT,
                tags TEXT,
                priority TEXT,
                due_at TEXT,
                estimated_minutes INTEGER,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                starts_at TEXT NOT NULL,
                ends_at TEXT NOT NULL,
                notes TEXT,
                tags TEXT,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _now_iso_local() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def get_priority_rules(user_id: str) -> Dict[str, Any]:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT priority_rules FROM preferences WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            default_rules = {
                "default_task_priority": "medium",
                "tags_priority": {
                    "health": 3,
                    "finance": 3,
                    "family": 2,
                    "work": 2,
                    "deep_work": 2,
                    "admin": 1,
                    "social": 1,
                },
                "due_date_weight": 3,
                "priority_weight": 4,
                "effort_weight": 1,
                "avoid_conflicts": True,
                "prefer_morning_for": ["deep_work", "work"],
                "prefer_evening_for": ["health", "gym"],
                "default_estimated_minutes": 30,
            }
            conn.execute(
                "INSERT OR REPLACE INTO preferences(user_id, priority_rules) VALUES(?, ?)",
                (user_id, json.dumps(default_rules)),
            )
            conn.commit()
            return default_rules
        return json.loads(row["priority_rules"])
    finally:
        conn.close()


def set_priority_rules(user_id: str, rules: Dict[str, Any]) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO preferences(user_id, priority_rules) VALUES(?, ?)",
            (user_id, json.dumps(rules)),
        )
        conn.commit()
    finally:
        conn.close()


def create_task(
    user_id: str,
    title: str,
    notes: Optional[str] = None,
    tags: Optional[List[str]] = None,
    priority: Optional[str] = None,
    due_at: Optional[str] = None,
    estimated_minutes: Optional[int] = None,
) -> int:
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO tasks(title, notes, tags, priority, due_at, estimated_minutes, status, created_at)
            VALUES(?, ?, ?, ?, ?, ?, 'open', ?)
            """,
            (
                title,
                notes,
                json.dumps(tags or []),
                priority,
                due_at,
                estimated_minutes,
                _now_iso_local(),
            ),
        )
        task_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.commit()
        return task_id
    finally:
        conn.close()


def list_tasks(user_id: str, status: str = "open") -> List[Dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC",
            (status,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def complete_task(task_id: int) -> None:
    conn = _connect()
    try:
        conn.execute("UPDATE tasks SET status = 'done' WHERE id = ?", (task_id,))
        conn.commit()
    finally:
        conn.close()


def create_event(
    user_id: str,
    title: str,
    starts_at: str,
    ends_at: str,
    notes: Optional[str] = None,
    tags: Optional[List[str]] = None,
    source: str = "local",
) -> int:
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO events(title, starts_at, ends_at, notes, tags, source, created_at)
            VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (title, starts_at, ends_at, notes, json.dumps(tags or []), source, _now_iso_local()),
        )
        event_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.commit()
        return event_id
    finally:
        conn.close()


def list_events_between(user_id: str, start_iso: str, end_iso: str) -> List[Tuple[str, str]]:
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT starts_at, ends_at FROM events
            WHERE starts_at < ? AND ends_at > ?
            ORDER BY starts_at ASC
            """,
            (end_iso, start_iso),
        ).fetchall()
        return [(r["starts_at"], r["ends_at"]) for r in rows]
    finally:
        conn.close()
