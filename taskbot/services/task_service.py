from __future__ import annotations

from datetime import timedelta
from typing import Optional, Tuple

from taskbot.database.db import get_connection
from taskbot.utils.datetime_parser import now_local, to_storage_string


TaskListResult = Tuple[list[dict], int]

DEFAULT_REMINDER_MINUTES = 5


def _row_to_task(row) -> dict:
    return dict(row)


def create_task(
    user_id: str,
    title: str,
    description: Optional[str],
    due_at: Optional[str],
    priority: str,
) -> int:
    now_str = to_storage_string(now_local())
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO tasks (user_id, title, description, status, priority, due_at, created_at, updated_at, completed_at)
            VALUES (?, ?, ?, 'todo', ?, ?, ?, ?, NULL)
            """,
            (user_id, title, description, priority, due_at, now_str, now_str),
        )
        conn.commit()
        return int(cursor.lastrowid)


def list_tasks(
    user_id: str,
    list_type: str,
    page: int,
    per_page: int = 10,
) -> TaskListResult:
    if page < 1:
        page = 1

    now = now_local()
    now_str = to_storage_string(now)
    today_str = now.date().isoformat()

    where = ["user_id = ?"]
    params: list = [user_id]

    if list_type == "todo":
        where.append("status = 'todo'")
    elif list_type == "done":
        where.append("status = 'done'")
    elif list_type == "today":
        where.append("status = 'todo'")
        where.append("due_at IS NOT NULL")
        where.append("date(due_at) = ?")
        params.append(today_str)
    elif list_type == "overdue":
        where.append("status = 'todo'")
        where.append("due_at IS NOT NULL")
        where.append("due_at < ?")
        params.append(now_str)
    else:
        raise ValueError("Invalid list_type")

    where_sql = " AND ".join(where)

    with get_connection() as conn:
        count_cursor = conn.execute(
            f"SELECT COUNT(*) AS total FROM tasks WHERE {where_sql}",
            params,
        )
        total = int(count_cursor.fetchone()[0])

        offset = (page - 1) * per_page
        rows = conn.execute(
            f"""
            SELECT * FROM tasks
            WHERE {where_sql}
            ORDER BY (due_at IS NULL) ASC, due_at ASC, id ASC
            LIMIT ? OFFSET ?
            """,
            params + [per_page, offset],
        ).fetchall()

    tasks = [_row_to_task(row) for row in rows]
    return tasks, total


def get_task_by_id(user_id: str, task_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, user_id),
        ).fetchone()
    if row is None:
        return None
    return _row_to_task(row)


def update_task(
    user_id: str,
    task_id: int,
    title: str,
    description: Optional[str],
    due_at: Optional[str],
    priority: str,
) -> bool:
    now_str = to_storage_string(now_local())
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE tasks
            SET title = ?, description = ?, due_at = ?, priority = ?, updated_at = ?, reminded_at = NULL
            WHERE id = ? AND user_id = ?
            """,
            (title, description, due_at, priority, now_str, task_id, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def complete_task(user_id: str, task_id: int) -> bool:
    now_str = to_storage_string(now_local())
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE tasks
            SET status = 'done', completed_at = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (now_str, now_str, task_id, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def reopen_task(user_id: str, task_id: int) -> bool:
    now_str = to_storage_string(now_local())
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE tasks
            SET status = 'todo', completed_at = NULL, updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (now_str, task_id, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_task(user_id: str, task_id: int) -> bool:
    # MVPでは物理削除。将来的には archived フラグで論理削除に拡張可能。
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def count_task_summary(user_id: str) -> dict:
    now = now_local()
    now_str = to_storage_string(now)
    today_str = now.date().isoformat()

    with get_connection() as conn:
        todo_count = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'todo'",
            (user_id,),
        ).fetchone()[0]

        due_today = conn.execute(
            """
            SELECT COUNT(*) FROM tasks
            WHERE user_id = ? AND status = 'todo' AND due_at IS NOT NULL AND date(due_at) = ?
            """,
            (user_id, today_str),
        ).fetchone()[0]

        overdue = conn.execute(
            """
            SELECT COUNT(*) FROM tasks
            WHERE user_id = ? AND status = 'todo' AND due_at IS NOT NULL AND due_at < ?
            """,
            (user_id, now_str),
        ).fetchone()[0]

    return {
        "todo_count": int(todo_count),
        "due_today": int(due_today),
        "overdue": int(overdue),
    }


def list_upcoming_reminders(max_minutes: int, limit: int = 200) -> list[dict]:
    if max_minutes <= 0:
        return []

    now = now_local()
    now_str = to_storage_string(now)
    window_end = now + timedelta(minutes=max_minutes)
    window_end_str = to_storage_string(window_end)

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM tasks
            WHERE status = 'todo'
              AND due_at IS NOT NULL
              AND reminded_at IS NULL
              AND due_at >= ?
              AND due_at <= ?
            ORDER BY due_at ASC
            LIMIT ?
            """,
            (now_str, window_end_str, limit),
        ).fetchall()

    return [_row_to_task(row) for row in rows]


def mark_task_reminded(user_id: str, task_id: int) -> bool:
    now_str = to_storage_string(now_local())
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE tasks
            SET reminded_at = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (now_str, now_str, task_id, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def get_user_settings(user_id: str) -> dict:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM user_settings WHERE user_id = ?",
            (user_id,),
        ).fetchone()

    if row is None:
        return {
            "user_id": user_id,
            "reminders_enabled": 1,
            "reminder_minutes": DEFAULT_REMINDER_MINUTES,
        }

    return dict(row)


def upsert_user_settings(
    user_id: str,
    reminders_enabled: bool,
    reminder_minutes: int,
) -> None:
    now_str = to_storage_string(now_local())
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO user_settings (user_id, reminders_enabled, reminder_minutes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                reminders_enabled = excluded.reminders_enabled,
                reminder_minutes = excluded.reminder_minutes,
                updated_at = excluded.updated_at
            """,
            (
                user_id,
                1 if reminders_enabled else 0,
                int(reminder_minutes),
                now_str,
                now_str,
            ),
        )
        conn.commit()


def get_max_reminder_minutes() -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT MAX(reminder_minutes) FROM user_settings WHERE reminders_enabled = 1"
        ).fetchone()

    if row is None or row[0] is None:
        return DEFAULT_REMINDER_MINUTES

    return max(DEFAULT_REMINDER_MINUTES, int(row[0]))
