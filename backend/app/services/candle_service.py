from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.time import ensure_aware_utc, utc_now
from app.db.models import PriceCandle, PriceTick


SUPPORTED_INTERVALS = [60, 300, 600, 900, 1800, 3600]


def _bucket_start(value: datetime, interval_seconds: int) -> datetime:
    value = ensure_aware_utc(value)
    timestamp = int(value.timestamp())
    bucket_timestamp = timestamp - (timestamp % interval_seconds)
    return datetime.fromtimestamp(bucket_timestamp, timezone.utc)


def update_candles_for_tick(db: Session, tick: PriceTick) -> None:
    price = Decimal(tick.price)
    fetched_at = ensure_aware_utc(tick.fetched_at)
    for interval in SUPPORTED_INTERVALS:
        bucket = _bucket_start(fetched_at, interval)
        candle = db.scalar(
            select(PriceCandle).where(
                PriceCandle.interval_seconds == interval,
                PriceCandle.bucket_start == bucket,
            )
        )
        if candle is None:
            db.add(
                PriceCandle(
                    interval_seconds=interval,
                    bucket_start=bucket,
                    open=price,
                    high=price,
                    low=price,
                    close=price,
                    count=1,
                    updated_at=utc_now(),
                )
            )
        else:
            candle.high = max(Decimal(candle.high), price)
            candle.low = min(Decimal(candle.low), price)
            candle.close = price
            candle.count += 1
            candle.updated_at = utc_now()


def candles_query(interval_seconds: int) -> Select[tuple[PriceCandle]]:
    return select(PriceCandle).where(PriceCandle.interval_seconds == interval_seconds)

