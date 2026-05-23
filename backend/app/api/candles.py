from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import PriceCandle
from app.db.session import get_db
from app.schemas.market import CandleResponse
from app.services.candle_service import SUPPORTED_INTERVALS
from app.services.settings_service import get_int_setting


router = APIRouter(prefix="/candles", tags=["分钟线"])


@router.get("", response_model=list[CandleResponse])
def candles(
    interval: int = Query(default=300),
    limit: int = Query(default=300, ge=1, le=2000),
    start: datetime | None = None,
    end: datetime | None = None,
    db: Session = Depends(get_db),
) -> list[PriceCandle]:
    if interval not in SUPPORTED_INTERVALS:
        interval = 300
    stmt = select(PriceCandle).where(PriceCandle.interval_seconds == interval)
    window_hours = get_int_setting(db, "market_visualization_window_hours", 48)
    effective_start = start
    if effective_start is None and end is None:
        effective_start = datetime.now().astimezone() - timedelta(hours=window_hours)
    if effective_start is not None:
        stmt = stmt.where(PriceCandle.bucket_start >= effective_start)
    if end is not None:
        stmt = stmt.where(PriceCandle.bucket_start <= end)
    stmt = stmt.order_by(PriceCandle.bucket_start.desc()).limit(limit)
    return list(db.scalars(stmt).all())
