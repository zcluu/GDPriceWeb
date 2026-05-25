from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.schemas.common import APIModel


class PriceTickResponse(APIModel):
    id: int
    source: str
    price: Decimal
    fetched_at: datetime
    remote_time: datetime | None = None
    created_at: datetime


class MinuteAverageResponse(APIModel):
    bucket_start: datetime
    average_price: Decimal
    count: int


class LatestPriceResponse(APIModel):
    price: Decimal | None = None
    source: str | None = None
    fetched_at: datetime | None = None
    collector_status: str
    failed_count: int
    last_error: str | None = None


class MarketStatusResponse(APIModel):
    collector_status: str
    failed_count: int
    last_error: str | None = None
    last_success_at: datetime | None = None
    next_trading_start_at: datetime | None = None
    refresh_interval_seconds: int
    visualization_window_hours: int
    trading_hours_description: str


class CandleResponse(APIModel):
    id: int
    interval_seconds: int
    bucket_start: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    count: int
    updated_at: datetime


class MarketSummaryResponse(APIModel):
    current_price: Decimal | None = None
    previous_price: Decimal | None = None
    change_amount: Decimal | None = None
    change_percent: Decimal | None = None
    today_high: Decimal | None = None
    today_low: Decimal | None = None
    fetched_at: datetime | None = None
