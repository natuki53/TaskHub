from __future__ import annotations

import sqlite3
from pathlib import Path

from taskbot.config import DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    columns = [row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column in columns:
        return
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def init_db() -> None:
    db_path = Path(DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    init_sql = Path(__file__).with_name("init.sql").read_text(encoding="utf-8")
    with get_connection() as conn:
        conn.executescript(init_sql)
        _ensure_column(conn, "tasks", "reminded_at", "reminded_at TEXT")
        conn.commit()
