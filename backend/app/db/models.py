from __future__ import annotations

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.session import Base


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)


class PriceTick(Base):
    __tablename__ = "price_ticks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(64), index=True, default="jd_gold")
    price: Mapped[Numeric] = mapped_column(Numeric(18, 4), nullable=False)
    fetched_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    remote_time: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)


class PriceCandle(Base):
    __tablename__ = "price_candles"
    __table_args__ = (
        UniqueConstraint("interval_seconds", "bucket_start", name="uq_candle_interval_bucket"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    interval_seconds: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    bucket_start: Mapped[DateTime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    open: Mapped[Numeric] = mapped_column(Numeric(18, 4), nullable=False)
    high: Mapped[Numeric] = mapped_column(Numeric(18, 4), nullable=False)
    low: Mapped[Numeric] = mapped_column(Numeric(18, 4), nullable=False)
    close: Mapped[Numeric] = mapped_column(Numeric(18, 4), nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    side: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    price: Mapped[Numeric] = mapped_column(Numeric(18, 4), nullable=False)
    grams: Mapped[Numeric] = mapped_column(Numeric(18, 4), nullable=False)
    fee: Mapped[Numeric] = mapped_column(Numeric(18, 4), default=0)
    traded_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    realized_pnl: Mapped[Numeric | None] = mapped_column(Numeric(18, 4), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    target_price: Mapped[Numeric | None] = mapped_column(Numeric(18, 4), nullable=True)
    target_percent: Mapped[Numeric | None] = mapped_column(Numeric(18, 4), nullable=True)
    target_amount: Mapped[Numeric | None] = mapped_column(Numeric(18, 4), nullable=True)
    window_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    step_thresholds: Mapped[str | None] = mapped_column(Text, nullable=True)
    reset_threshold_amount: Mapped[Numeric | None] = mapped_column(Numeric(18, 4), nullable=True)
    trigger_mode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notification_style: Mapped[str] = mapped_column(String(32), default="standard")
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=600)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_triggered_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    state: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    rule_name: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    price: Mapped[Numeric | None] = mapped_column(Numeric(18, 4), nullable=True)
    window_high: Mapped[Numeric | None] = mapped_column(Numeric(18, 4), nullable=True)
    window_low: Mapped[Numeric | None] = mapped_column(Numeric(18, 4), nullable=True)
    window_range: Mapped[Numeric | None] = mapped_column(Numeric(18, 4), nullable=True)
    triggered_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    sent: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)

