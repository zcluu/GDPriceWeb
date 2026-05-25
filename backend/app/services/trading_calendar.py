from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.time import ensure_aware_utc, utc_now
from app.services.settings_service import get_bool_setting, get_setting


def trading_zone(name: str | None = None) -> ZoneInfo:
    zone_name = name or settings.trading_timezone
    try:
        return ZoneInfo(zone_name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("Asia/Shanghai")


def is_accumulation_gold_trading_time(
    value: datetime | None = None,
    *,
    timezone_name: str | None = None,
) -> bool:
    """积存金交易时间：周一 09:00 至周六 02:00，按中国时间判断。"""

    zone = trading_zone(timezone_name)
    current = ensure_aware_utc(value or utc_now()).astimezone(zone)
    weekday = current.weekday()  # Monday=0, Sunday=6
    current_time = current.time()

    if weekday == 0:
        return current_time >= time(9, 0)
    if weekday in {1, 2, 3, 4}:
        return True
    if weekday == 5:
        return current_time < time(2, 0)
    return False


def should_collect_now(db: Session, value: datetime | None = None) -> bool:
    enabled = get_bool_setting(db, "accumulation_gold_trading_hours_enabled", True)
    if not enabled:
        return True
    timezone_name = get_setting(db, "trading_timezone", settings.trading_timezone)
    return is_accumulation_gold_trading_time(value, timezone_name=timezone_name)


def next_trading_start(
    value: datetime | None = None,
    *,
    timezone_name: str | None = None,
) -> datetime:
    zone = trading_zone(timezone_name)
    current = ensure_aware_utc(value or utc_now()).astimezone(zone)
    weekday = current.weekday()

    if is_accumulation_gold_trading_time(current, timezone_name=timezone_name):
        return current.astimezone(timezone.utc)

    if weekday == 0 and current.time() < time(9, 0):
        candidate = current.replace(hour=9, minute=0, second=0, microsecond=0)
    else:
        days_until_monday = (7 - weekday) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        monday = (current + timedelta(days=days_until_monday)).date()
        candidate = datetime.combine(monday, time(9, 0), tzinfo=zone)
    return candidate.astimezone(timezone.utc)


def trading_lookback_start(
    value: datetime | None = None,
    *,
    hours: int = 48,
    timezone_name: str | None = None,
) -> datetime:
    zone = trading_zone(timezone_name)
    cursor = ensure_aware_utc(value or utc_now()).astimezone(zone)
    cursor = cursor.replace(second=0, microsecond=0)
    remaining_minutes = max(1, hours) * 60

    while remaining_minutes > 0:
        cursor -= timedelta(minutes=1)
        if is_accumulation_gold_trading_time(cursor, timezone_name=timezone_name):
            remaining_minutes -= 1
    return cursor.astimezone(timezone.utc)


def trading_window_description() -> str:
    return "周一 09:00 至周六 02:00（中国时间）"
