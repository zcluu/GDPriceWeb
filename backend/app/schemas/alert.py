from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import APIModel


class AlertRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    type: str
    target_price: Decimal | None = None
    target_percent: Decimal | None = None
    target_amount: Decimal | None = None
    window_seconds: int | None = Field(default=None, ge=1)
    step_thresholds: list[dict[str, Any]] | None = None
    reset_threshold_amount: Decimal | None = None
    trigger_mode: str | None = None
    notification_style: str = "standard"
    cooldown_seconds: int = Field(default=600, ge=0)
    enabled: bool = True


class AlertRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    type: str | None = None
    target_price: Decimal | None = None
    target_percent: Decimal | None = None
    target_amount: Decimal | None = None
    window_seconds: int | None = Field(default=None, ge=1)
    step_thresholds: list[dict[str, Any]] | None = None
    reset_threshold_amount: Decimal | None = None
    trigger_mode: str | None = None
    notification_style: str | None = None
    cooldown_seconds: int | None = Field(default=None, ge=0)
    enabled: bool | None = None


class AlertRuleResponse(APIModel):
    id: int
    name: str
    type: str
    target_price: Decimal | None = None
    target_percent: Decimal | None = None
    target_amount: Decimal | None = None
    window_seconds: int | None = None
    step_thresholds: list[dict[str, Any]] | None = None
    reset_threshold_amount: Decimal | None = None
    trigger_mode: str | None = None
    notification_style: str
    cooldown_seconds: int
    enabled: bool
    last_triggered_at: datetime | None = None
    state: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class AlertEventResponse(APIModel):
    id: int
    rule_id: int | None = None
    rule_name: str
    event_type: str
    price: Decimal | None = None
    window_high: Decimal | None = None
    window_low: Decimal | None = None
    window_range: Decimal | None = None
    triggered_level: int | None = None
    message: str
    sent: bool
    sent_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime


class TestDingTalkRequest(BaseModel):
    message: str | None = None
