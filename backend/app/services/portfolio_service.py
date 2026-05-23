from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import PriceTick, Trade


ZERO = Decimal("0")


@dataclass
class PortfolioSnapshot:
    holding_grams: Decimal
    cost_amount: Decimal
    average_price: Decimal
    current_price: Decimal | None
    market_value: Decimal
    floating_pnl: Decimal
    floating_pnl_percent: Decimal
    realized_pnl: Decimal


def latest_price(db: Session) -> Decimal | None:
    tick = db.scalar(select(PriceTick).order_by(PriceTick.fetched_at.desc(), PriceTick.id.desc()))
    return Decimal(tick.price) if tick else None


def calculate_snapshot(db: Session, current_price: Decimal | None = None) -> PortfolioSnapshot:
    trades = db.scalars(select(Trade).order_by(Trade.traded_at.asc(), Trade.id.asc())).all()
    holding = ZERO
    cost = ZERO
    realized = ZERO

    for trade in trades:
        price = Decimal(trade.price)
        grams = Decimal(trade.grams)
        fee = Decimal(trade.fee or 0)
        if trade.side == "BUY":
            holding += grams
            cost += price * grams + fee
        elif trade.side == "SELL":
            if grams > holding:
                raise HTTPException(status_code=400, detail="历史交易记录存在超卖，无法计算持仓")
            avg = cost / holding if holding > 0 else ZERO
            removed_cost = avg * grams
            realized += price * grams - removed_cost - fee
            holding -= grams
            cost -= removed_cost
            if holding == 0:
                cost = ZERO

    if current_price is None:
        current_price = latest_price(db)
    average_price = cost / holding if holding > 0 else ZERO
    market_value = (current_price or ZERO) * holding
    floating_pnl = market_value - cost
    floating_percent = (floating_pnl / cost * Decimal("100")) if cost > 0 else ZERO

    return PortfolioSnapshot(
        holding_grams=holding,
        cost_amount=cost,
        average_price=average_price,
        current_price=current_price,
        market_value=market_value,
        floating_pnl=floating_pnl,
        floating_pnl_percent=floating_percent,
        realized_pnl=realized,
    )


def validate_trade_insert(db: Session, side: str, grams: Decimal) -> None:
    if side != "SELL":
        return
    snapshot = calculate_snapshot(db)
    if grams > snapshot.holding_grams:
        raise HTTPException(status_code=400, detail="卖出克重不能大于当前持仓克重")

