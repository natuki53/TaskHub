from __future__ import annotations

from datetime import datetime
from typing import Optional


def parse_due_datetime(text: Optional[str]) -> Optional[datetime]:
    if text is None:
        return None

    raw = text.strip()
    if not raw:
        return None

    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(raw, fmt)
            if fmt == "%Y-%m-%d":
                parsed = parsed.replace(hour=0, minute=0)
            return parsed
        except ValueError:
            continue

    raise ValueError("Invalid due date format. Use YYYY-MM-DD or YYYY-MM-DD HH:MM")


def to_storage_string(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M")


def now_local() -> datetime:
    return datetime.now()
