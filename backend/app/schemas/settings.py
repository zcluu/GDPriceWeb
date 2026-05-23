from __future__ import annotations

from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    refresh_interval_seconds: int
    history_retention_days: int
    default_chart_interval_seconds: int
    market_visualization_window_hours: int
    accumulation_gold_trading_hours_enabled: bool
    trading_timezone: str
    dingtalk_enabled: bool
    dingtalk_webhook_masked: str | None = None
    dingtalk_secret_configured: bool
    dingtalk_message_style: str
    default_alert_cooldown_seconds: int
    default_range_window_seconds: int
    default_range_steps: str
    rise_color: str
    fall_color: str


class SettingsUpdate(BaseModel):
    refresh_interval_seconds: int | None = Field(default=None, ge=5, le=3600)
    history_retention_days: int | None = Field(default=None, ge=1, le=3650)
    default_chart_interval_seconds: int | None = Field(default=None, ge=60)
    market_visualization_window_hours: int | None = Field(default=None, ge=1, le=168)
    accumulation_gold_trading_hours_enabled: bool | None = None
    trading_timezone: str | None = None
    dingtalk_enabled: bool | None = None
    dingtalk_webhook: str | None = None
    dingtalk_secret: str | None = None
    dingtalk_message_style: str | None = None
    default_alert_cooldown_seconds: int | None = Field(default=None, ge=0)
    default_range_window_seconds: int | None = Field(default=None, ge=60)
    default_range_steps: str | None = None
    rise_color: str | None = None
    fall_color: str | None = None
