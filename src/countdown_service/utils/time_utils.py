"""Utilities for working with dates, times and countdowns."""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Tuple


def coerce_timezone(name: str | None) -> ZoneInfo:
    """Return a timezone instance for the provided name, defaulting to UTC."""

    tz_name = name or "UTC"
    try:
        return ZoneInfo(tz_name)
    except Exception as exc:
        raise ValueError(f"Unknown timezone: {tz_name}") from exc


def get_time_remaining(target: datetime, tz: ZoneInfo) -> Tuple[timedelta, datetime]:
    """Return time delta until target (aware) and the normalized target datetime."""

    if target.tzinfo is None:
        target = target.replace(tzinfo=tz)
    else:
        target = target.astimezone(tz)
    now = datetime.now(tz=tz)
    return max(target - now, timedelta(0)), target


def humanize_delta(delta: timedelta) -> str:
    """Return a human readable representation of a timedelta."""

    seconds = int(delta.total_seconds())
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or parts:
        parts.append(f"{hours:02}h")
    if minutes or parts:
        parts.append(f"{minutes:02}m")
    parts.append(f"{seconds:02}s")
    return " ".join(parts)
