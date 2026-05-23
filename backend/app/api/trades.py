from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.core.time import utc_now
from app.db.models import Trade
from app.db.session import get_db
from app.schemas.trade import PortfolioResponse, TradeCreate, TradeResponse, TradeUpdate
from app.services.portfolio_service import calculate_snapshot, validate_trade_insert


router = APIRouter(prefix="/trades", tags=["交易"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[TradeResponse])
def list_trades(db: Session = Depends(get_db)) -> list[Trade]:
    return list(db.scalars(select(Trade).order_by(Trade.traded_at.desc(), Trade.id.desc())).all())


@router.post("", response_model=TradeResponse)
def create_trade(payload: TradeCreate, db: Session = Depends(get_db)) -> Trade:
    validate_trade_insert(db, payload.side, payload.grams)
    trade = Trade(
        side=payload.side,
        price=payload.price,
        grams=payload.grams,
        fee=payload.fee,
        traded_at=payload.normalized_traded_at(),
        note=payload.note,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade


@router.get("/portfolio", response_model=PortfolioResponse)
def portfolio(db: Session = Depends(get_db)) -> PortfolioResponse:
    return PortfolioResponse(**calculate_snapshot(db).__dict__)


@router.put("/{trade_id}", response_model=TradeResponse)
def update_trade(trade_id: int, payload: TradeUpdate, db: Session = Depends(get_db)) -> Trade:
    trade = db.get(Trade, trade_id)
    if trade is None:
        raise HTTPException(status_code=404, detail="交易记录不存在")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(trade, key, value)
    trade.updated_at = utc_now()
    db.add(trade)
    try:
        calculate_snapshot(db)
    except HTTPException:
        db.rollback()
        raise
    db.commit()
    db.refresh(trade)
    return trade


@router.delete("/{trade_id}")
def delete_trade(trade_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    trade = db.get(Trade, trade_id)
    if trade is None:
        raise HTTPException(status_code=404, detail="交易记录不存在")
    db.delete(trade)
    try:
        calculate_snapshot(db)
    except HTTPException:
        db.rollback()
        raise
    db.commit()
    return {"message": "已删除交易记录"}
