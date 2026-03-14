from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Optional


NONE_KEYWORDS = {"", "なし", "無し", "none", "null", "nil", "-", "未設定", "off"}


def _with_year_rollover(
    now: datetime,
    year: Optional[int],
    month: int,
    day: int,
    hour: int,
    minute: int,
    has_time: bool,
) -> datetime:
    if year is not None:
        return datetime(year, month, day, hour, minute)

    candidate = datetime(now.year, month, day, hour, minute)
    if has_time and candidate >= now:
        return candidate
    if not has_time and candidate.date() >= now.date():
        return candidate
    return datetime(now.year + 1, month, day, hour, minute)


def _parse_hhmm(raw: str) -> tuple[int, int]:
    hour_text, minute_text = raw.split(":", 1)
    hour = int(hour_text)
    minute = int(minute_text)
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError
    return hour, minute


def parse_due_datetime(text: Optional[str]) -> Optional[datetime]:
    if text is None:
        return None

    raw = text.strip()
    if raw.lower() in NONE_KEYWORDS or raw in NONE_KEYWORDS:
        return None

    now = now_local().replace(second=0, microsecond=0)
    compact = re.sub(r"\s+", " ", raw)

    # Relative format: 10分後 / 2時間後 / 3日後
    m = re.fullmatch(r"(\d+)\s*(分|時間|日)後", compact)
    if m:
        amount = int(m.group(1))
        unit = m.group(2)
        delta = timedelta()
        if unit == "分":
            delta = timedelta(minutes=amount)
        elif unit == "時間":
            delta = timedelta(hours=amount)
        elif unit == "日":
            delta = timedelta(days=amount)
        return now + delta

    # 今日 / 明日 / 明後日 + optional HH:MM
    m = re.fullmatch(r"(今日|明日|明後日)(?:\s+(\d{1,2}:\d{2}))?", compact)
    if m:
        day_word = m.group(1)
        time_text = m.group(2)
        offset_map = {"今日": 0, "明日": 1, "明後日": 2}
        base = (now + timedelta(days=offset_map[day_word])).date()
        hour, minute = (0, 0)
        if time_text:
            hour, minute = _parse_hhmm(time_text)
        return datetime(base.year, base.month, base.day, hour, minute)

    # HH:MM only (today if future, otherwise tomorrow)
    m = re.fullmatch(r"(\d{1,2}:\d{2})", compact)
    if m:
        hour, minute = _parse_hhmm(m.group(1))
        candidate = now.replace(hour=hour, minute=minute)
        if candidate >= now:
            return candidate
        return candidate + timedelta(days=1)

    # x月x日 [HH:MM] / [yyyy年]x月x日 [HH:MM]
    m = re.fullmatch(
        r"(?:(\d{4})\s*年\s*)?(\d{1,2})\s*月\s*(\d{1,2})\s*日(?:\s+(\d{1,2}:\d{2}))?",
        compact,
    )
    if m:
        year = int(m.group(1)) if m.group(1) else None
        month = int(m.group(2))
        day = int(m.group(3))
        hour, minute = (0, 0)
        has_time = False
        if m.group(4):
            has_time = True
            hour, minute = _parse_hhmm(m.group(4))
        return _with_year_rollover(
            now, year, month, day, hour, minute, has_time=has_time
        )

    # mm/dd [HH:MM] / yyyy/mm/dd [HH:MM]
    m = re.fullmatch(
        r"(?:(\d{4})/)?(\d{1,2})/(\d{1,2})(?:\s+(\d{1,2}:\d{2}))?",
        compact,
    )
    if m:
        year = int(m.group(1)) if m.group(1) else None
        month = int(m.group(2))
        day = int(m.group(3))
        hour, minute = (0, 0)
        has_time = False
        if m.group(4):
            has_time = True
            hour, minute = _parse_hhmm(m.group(4))
        return _with_year_rollover(
            now, year, month, day, hour, minute, has_time=has_time
        )

    for fmt in (
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M",
        "%Y.%m.%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y.%m.%d",
    ):
        try:
            parsed = datetime.strptime(compact, fmt)
            if fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
                parsed = parsed.replace(hour=0, minute=0)
            return parsed
        except ValueError:
            continue

    raise ValueError(
        "Invalid due date format. Examples: 2026-03-21 14:37 / 3/21 14:37 / 3月21日 / 明日 09:15 / 10分後"
    )


def to_storage_string(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M")


def now_local() -> datetime:
    return datetime.now()
