from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.core.time import utc_now
from app.schemas.common import APIModel


class TradeCreate(BaseModel):
    side: str
    price: Decimal = Field(gt=0)
    grams: Decimal = Field(gt=0)
    fee: Decimal = Field(default=Decimal("0"), ge=0)
    traded_at: datetime | None = None
    note: str | None = None

    @field_validator("side")
    @classmethod
    def validate_side(cls, value: str) -> str:
        value = value.upper()
        if value not in {"BUY", "SELL"}:
            raise ValueError("交易类型只能是 BUY 或 SELL")
        return value

    def normalized_traded_at(self) -> datetime:
        return self.traded_at or utc_now()


class TradeUpdate(BaseModel):
    side: str | None = None
    price: Decimal | None = Field(default=None, gt=0)
    grams: Decimal | None = Field(default=None, gt=0)
    fee: Decimal | None = Field(default=None, ge=0)
    traded_at: datetime | None = None
    note: str | None = None

    @field_validator("side")
    @classmethod
    def validate_side(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.upper()
        if value not in {"BUY", "SELL"}:
            raise ValueError("交易类型只能是 BUY 或 SELL")
        return value


class TradeResponse(APIModel):
    id: int
    side: str
    price: Decimal
    grams: Decimal
    fee: Decimal
    traded_at: datetime
    note: str | None = None
    realized_pnl: Decimal | None = None
    created_at: datetime
    updated_at: datetime


class PortfolioResponse(APIModel):
    holding_grams: Decimal
    cost_amount: Decimal
    average_price: Decimal
    current_price: Decimal | None
    market_value: Decimal
    floating_pnl: Decimal
    floating_pnl_percent: Decimal
    realized_pnl: Decimal

