from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.time import utc_now
from app.db.models import Setting


DEFAULT_SETTINGS = {
    "refresh_interval_seconds": str(settings.price_refresh_interval_seconds),
    "history_retention_days": str(settings.price_history_retention_days),
    "default_chart_interval_seconds": "300",
    "market_visualization_window_hours": str(settings.market_visualization_window_hours),
    "accumulation_gold_trading_hours_enabled": str(
        settings.accumulation_gold_trading_hours_enabled
    ).lower(),
    "trading_timezone": settings.trading_timezone,
    "dingtalk_enabled": str(settings.dingtalk_enabled).lower(),
    "dingtalk_webhook": settings.dingtalk_webhook,
    "dingtalk_secret": settings.dingtalk_secret,
    "dingtalk_message_style": settings.dingtalk_message_style,
    "default_alert_cooldown_seconds": str(settings.default_alert_cooldown_seconds),
    "default_range_window_seconds": str(settings.default_range_window_seconds),
    "default_range_steps": settings.default_range_steps,
    "rise_color": "红色",
    "fall_color": "绿色",
}


def get_setting(db: Session, key: str, default: str | None = None) -> str:
    row = db.get(Setting, key)
    if row is None:
        return DEFAULT_SETTINGS.get(key, default or "")
    return row.value


def set_setting(db: Session, key: str, value: str) -> Setting:
    row = db.get(Setting, key)
    if row is None:
        row = Setting(key=key, value=value, updated_at=utc_now())
        db.add(row)
    else:
        row.value = value
        row.updated_at = utc_now()
    return row


def get_int_setting(db: Session, key: str, default: int) -> int:
    try:
        return int(get_setting(db, key, str(default)))
    except ValueError:
        return default


def get_bool_setting(db: Session, key: str, default: bool) -> bool:
    value = get_setting(db, key, str(default).lower())
    return value.strip().lower() in {"1", "true", "yes", "on", "y"}


def mask_secret(value: str) -> str | None:
    if not value:
        return None
    if len(value) <= 12:
        return value[:2] + "******" + value[-2:]
    return value[:6] + "******" + value[-6:]


def get_public_settings(db: Session) -> dict[str, object]:
    webhook = get_setting(db, "dingtalk_webhook", "")
    secret = get_setting(db, "dingtalk_secret", "")
    return {
        "refresh_interval_seconds": get_int_setting(db, "refresh_interval_seconds", 30),
        "history_retention_days": get_int_setting(db, "history_retention_days", 30),
        "default_chart_interval_seconds": get_int_setting(
            db, "default_chart_interval_seconds", 300
        ),
        "market_visualization_window_hours": get_int_setting(
            db, "market_visualization_window_hours", 48
        ),
        "accumulation_gold_trading_hours_enabled": get_bool_setting(
            db, "accumulation_gold_trading_hours_enabled", True
        ),
        "trading_timezone": get_setting(db, "trading_timezone", "Asia/Shanghai"),
        "dingtalk_enabled": get_bool_setting(db, "dingtalk_enabled", False),
        "dingtalk_webhook_masked": mask_secret(webhook),
        "dingtalk_secret_configured": bool(secret),
        "dingtalk_message_style": get_setting(db, "dingtalk_message_style", "standard"),
        "default_alert_cooldown_seconds": get_int_setting(
            db, "default_alert_cooldown_seconds", 600
        ),
        "default_range_window_seconds": get_int_setting(
            db, "default_range_window_seconds", 300
        ),
        "default_range_steps": get_setting(
            db, "default_range_steps", settings.default_range_steps
        ),
        "rise_color": get_setting(db, "rise_color", "红色"),
        "fall_color": get_setting(db, "fall_color", "绿色"),
    }
