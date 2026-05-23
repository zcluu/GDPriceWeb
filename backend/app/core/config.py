from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "y"}


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


def _list_env(name: str, default: list[str] | None = None) -> list[str]:
    value = os.getenv(name)
    if not value:
        return default or []
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "金价守望")
    app_env: str = os.getenv("APP_ENV", "development")
    app_public_url: str = os.getenv("APP_PUBLIC_URL", "http://localhost:8000")
    app_secret_key: str = os.getenv("APP_SECRET_KEY", "change-me-dev-secret")
    app_password_hash: str = os.getenv("APP_PASSWORD_HASH", "")
    app_password: str = os.getenv("APP_PASSWORD", "admin123")
    jwt_expire_minutes: int = _int_env("JWT_EXPIRE_MINUTES", 720)

    database_url: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{(BASE_DIR / 'runtime' / 'watchgold.db').as_posix()}",
    )

    price_source: str = os.getenv("PRICE_SOURCE", "jd_gold")
    price_refresh_interval_seconds: int = _int_env("PRICE_REFRESH_INTERVAL_SECONDS", 30)
    price_request_timeout_seconds: int = _int_env("PRICE_REQUEST_TIMEOUT_SECONDS", 5)
    price_history_retention_days: int = _int_env("PRICE_HISTORY_RETENTION_DAYS", 30)
    market_visualization_window_hours: int = _int_env("MARKET_VISUALIZATION_WINDOW_HOURS", 48)
    accumulation_gold_trading_hours_enabled: bool = _bool_env(
        "ACCUMULATION_GOLD_TRADING_HOURS_ENABLED", True
    )
    trading_timezone: str = os.getenv("TRADING_TIMEZONE", "Asia/Shanghai")
    price_provider_url: str = os.getenv(
        "PRICE_PROVIDER_URL",
        "https://api.jdjygold.com/gw/generic/hj/h5/m/latestPrice",
    )

    dingtalk_enabled: bool = _bool_env("DINGTALK_ENABLED", False)
    dingtalk_webhook: str = os.getenv("DINGTALK_WEBHOOK", "")
    dingtalk_secret: str = os.getenv("DINGTALK_SECRET", "")
    dingtalk_at_mobiles: list[str] = field(
        default_factory=lambda: _list_env("DINGTALK_AT_MOBILES")
    )
    dingtalk_is_at_all: bool = _bool_env("DINGTALK_IS_AT_ALL", False)
    dingtalk_message_style: str = os.getenv("DINGTALK_MESSAGE_STYLE", "standard")

    default_alert_cooldown_seconds: int = _int_env("DEFAULT_ALERT_COOLDOWN_SECONDS", 600)
    default_range_window_seconds: int = _int_env("DEFAULT_RANGE_WINDOW_SECONDS", 300)
    default_range_steps: str = os.getenv(
        "DEFAULT_RANGE_STEPS", "3:轻微波动,5:明显波动,8:剧烈波动"
    )

    cors_origins: list[str] = field(
        default_factory=lambda: _list_env("CORS_ORIGINS", ["http://localhost:5173"])
    )
    disable_collector: bool = _bool_env("WATCHGOLD_DISABLE_COLLECTOR", False)


settings = Settings()
