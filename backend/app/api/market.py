from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import PriceTick
from app.db.session import get_db
from app.schemas.market import (
    LatestPriceResponse,
    MarketStatusResponse,
    MarketSummaryResponse,
    PriceTickResponse,
)
from app.services.price_collector import collector
from app.services.settings_service import get_int_setting, get_setting
from app.services.trading_calendar import trading_window_description


router = APIRouter(prefix="/market", tags=["行情"])


@router.get("/latest", response_model=LatestPriceResponse)
def latest(db: Session = Depends(get_db)) -> LatestPriceResponse:
    tick = db.scalar(select(PriceTick).order_by(PriceTick.fetched_at.desc(), PriceTick.id.desc()))
    if tick is None:
        return LatestPriceResponse(
            collector_status=collector.status.status,
            failed_count=collector.status.failed_count,
            last_error=collector.status.last_error,
        )
    return LatestPriceResponse(
        price=tick.price,
        source=tick.source,
        fetched_at=tick.fetched_at,
        collector_status=collector.status.status,
        failed_count=collector.status.failed_count,
        last_error=collector.status.last_error,
    )


@router.get("/ticks", response_model=list[PriceTickResponse])
def ticks(
    limit: int = Query(default=500, ge=1, le=5000),
    start: datetime | None = None,
    end: datetime | None = None,
    db: Session = Depends(get_db),
) -> list[PriceTick]:
    stmt = select(PriceTick)
    window_hours = get_int_setting(db, "market_visualization_window_hours", 48)
    effective_start = start
    if effective_start is None and end is None:
        effective_start = datetime.now().astimezone() - timedelta(hours=window_hours)
    if effective_start is not None:
        stmt = stmt.where(PriceTick.fetched_at >= effective_start)
    if end is not None:
        stmt = stmt.where(PriceTick.fetched_at <= end)
    stmt = stmt.order_by(PriceTick.fetched_at.desc(), PriceTick.id.desc()).limit(limit)
    return list(db.scalars(stmt).all())


@router.get("/status", response_model=MarketStatusResponse)
def status(db: Session = Depends(get_db)) -> MarketStatusResponse:
    return MarketStatusResponse(
        collector_status=collector.status.status,
        failed_count=collector.status.failed_count,
        last_error=collector.status.last_error,
        last_success_at=collector.status.last_success_at,
        next_trading_start_at=collector.status.next_trading_start_at,
        refresh_interval_seconds=get_int_setting(db, "refresh_interval_seconds", 30),
        visualization_window_hours=get_int_setting(db, "market_visualization_window_hours", 48),
        trading_hours_description=trading_window_description(),
    )


@router.get("/summary", response_model=MarketSummaryResponse)
def summary(db: Session = Depends(get_db)) -> MarketSummaryResponse:
    latest_ticks = list(
        db.scalars(
            select(PriceTick).order_by(PriceTick.fetched_at.desc(), PriceTick.id.desc()).limit(2)
        ).all()
    )
    if not latest_ticks:
        return MarketSummaryResponse()
    latest = latest_ticks[0]
    previous = latest_ticks[1] if len(latest_ticks) > 1 else None
    latest_price = Decimal(latest.price)
    previous_price = Decimal(previous.price) if previous else None
    change_amount = latest_price - previous_price if previous_price is not None else None
    change_percent = (
        change_amount / previous_price * Decimal("100")
        if change_amount is not None and previous_price and previous_price > 0
        else None
    )

    timezone_name = get_setting(db, "trading_timezone", "Asia/Shanghai")
    now_local = datetime.now(ZoneInfo(timezone_name))
    day_start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    day_start = day_start_local.astimezone(ZoneInfo("UTC"))
    today_ticks = list(
        db.scalars(select(PriceTick).where(PriceTick.fetched_at >= day_start)).all()
    )
    prices = [Decimal(tick.price) for tick in today_ticks]
    return MarketSummaryResponse(
        current_price=latest_price,
        previous_price=previous_price,
        change_amount=change_amount,
        change_percent=change_percent,
        today_high=max(prices) if prices else latest_price,
        today_low=min(prices) if prices else latest_price,
        fetched_at=latest.fetched_at,
    )
