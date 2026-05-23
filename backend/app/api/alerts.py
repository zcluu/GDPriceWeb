from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.core.time import utc_now
from app.db.models import AlertEvent, AlertRule
from app.db.session import get_db
from app.schemas.alert import (
    AlertEventResponse,
    AlertRuleCreate,
    AlertRuleResponse,
    AlertRuleUpdate,
    TestDingTalkRequest,
)
from app.services.dingtalk_notifier import DingTalkNotifier


router = APIRouter(prefix="/alerts", tags=["提醒"], dependencies=[Depends(get_current_user)])


def _rule_to_response(rule: AlertRule) -> AlertRuleResponse:
    steps: list[dict[str, Any]] | None = None
    state: dict[str, Any] | None = None
    if rule.step_thresholds:
        try:
            steps = json.loads(rule.step_thresholds)
        except json.JSONDecodeError:
            steps = None
    if rule.state:
        try:
            state = json.loads(rule.state)
        except json.JSONDecodeError:
            state = None
    return AlertRuleResponse(
        id=rule.id,
        name=rule.name,
        type=rule.type,
        target_price=rule.target_price,
        target_percent=rule.target_percent,
        target_amount=rule.target_amount,
        window_seconds=rule.window_seconds,
        step_thresholds=steps,
        reset_threshold_amount=rule.reset_threshold_amount,
        trigger_mode=rule.trigger_mode,
        notification_style=rule.notification_style,
        cooldown_seconds=rule.cooldown_seconds,
        enabled=rule.enabled,
        last_triggered_at=rule.last_triggered_at,
        state=state,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.get("/rules", response_model=list[AlertRuleResponse])
def list_rules(db: Session = Depends(get_db)) -> list[AlertRuleResponse]:
    rules = db.scalars(select(AlertRule).order_by(AlertRule.id.asc())).all()
    return [_rule_to_response(rule) for rule in rules]


@router.post("/rules", response_model=AlertRuleResponse)
def create_rule(payload: AlertRuleCreate, db: Session = Depends(get_db)) -> AlertRuleResponse:
    rule = AlertRule(
        name=payload.name,
        type=payload.type.upper(),
        target_price=payload.target_price,
        target_percent=payload.target_percent,
        target_amount=payload.target_amount,
        window_seconds=payload.window_seconds,
        step_thresholds=json.dumps(payload.step_thresholds, ensure_ascii=False)
        if payload.step_thresholds is not None
        else None,
        reset_threshold_amount=payload.reset_threshold_amount,
        trigger_mode=payload.trigger_mode,
        notification_style=payload.notification_style,
        cooldown_seconds=payload.cooldown_seconds,
        enabled=payload.enabled,
        state=json.dumps({"last_step_index": None, "last_crossed_price": None}, ensure_ascii=False)
        if payload.type.upper() == "RANGE_STEP_AMOUNT"
        else None,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return _rule_to_response(rule)


@router.put("/rules/{rule_id}", response_model=AlertRuleResponse)
def update_rule(
    rule_id: int, payload: AlertRuleUpdate, db: Session = Depends(get_db)
) -> AlertRuleResponse:
    rule = db.get(AlertRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="提醒规则不存在")
    data = payload.model_dump(exclude_unset=True)
    old_type = rule.type.upper()
    old_step_key = (rule.target_price, rule.target_amount)
    if "step_thresholds" in data:
        value = data.pop("step_thresholds")
        rule.step_thresholds = (
            json.dumps(value, ensure_ascii=False) if value is not None else None
        )
    if "type" in data and data["type"] is not None:
        data["type"] = str(data["type"]).upper()
    for key, value in data.items():
        setattr(rule, key, value)
    new_type = rule.type.upper()
    new_step_key = (rule.target_price, rule.target_amount)
    if new_type == "RANGE_STEP_AMOUNT":
        if old_type != new_type or old_step_key != new_step_key:
            rule.state = json.dumps(
                {"last_step_index": None, "last_crossed_price": None},
                ensure_ascii=False,
            )
        rule.window_seconds = None
        rule.step_thresholds = None
        rule.reset_threshold_amount = None
    elif old_type == "RANGE_STEP_AMOUNT" or rule.state:
        rule.state = None
    rule.updated_at = utc_now()
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return _rule_to_response(rule)


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    rule = db.get(AlertRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="提醒规则不存在")
    db.delete(rule)
    db.commit()
    return {"message": "已删除提醒规则"}


@router.get("/events", response_model=list[AlertEventResponse])
def list_events(
    limit: int = Query(default=200, ge=1, le=2000),
    db: Session = Depends(get_db),
) -> list[AlertEvent]:
    stmt = select(AlertEvent).order_by(AlertEvent.created_at.desc(), AlertEvent.id.desc()).limit(limit)
    return list(db.scalars(stmt).all())


@router.post("/test-dingtalk")
async def test_dingtalk(
    payload: TestDingTalkRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    text = payload.message or "金价守望测试消息\n\n如果你看到这条消息，说明钉钉机器人配置已经可用。"
    result = await DingTalkNotifier().send(db, title="金价守望测试消息", text=text)
    return {"sent": result.sent, "error_message": result.error_message}
