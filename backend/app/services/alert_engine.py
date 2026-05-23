from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, ROUND_FLOOR
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import ensure_aware_utc, utc_now
from app.db.models import AlertEvent, AlertRule, PriceTick
from app.services.dingtalk_notifier import DingTalkNotifier, build_price_alert_text, format_decimal
from app.services.portfolio_service import calculate_snapshot


@dataclass
class TriggerContext:
    rule: AlertRule
    message: str
    price: Decimal | None
    window_high: Decimal | None = None
    window_low: Decimal | None = None
    window_range: Decimal | None = None
    triggered_level: int | None = None
    state: dict[str, Any] | None = None


class AlertEngine:
    def __init__(self, notifier: DingTalkNotifier | None = None) -> None:
        self.notifier = notifier or DingTalkNotifier()

    async def evaluate(self, db: Session, latest_tick: PriceTick) -> list[AlertEvent]:
        events: list[AlertEvent] = []
        latest_price = Decimal(latest_tick.price)
        rules = db.scalars(
            select(AlertRule).where(AlertRule.enabled.is_(True)).order_by(AlertRule.id.asc())
        ).all()
        portfolio = calculate_snapshot(db, latest_price)
        for rule in rules:
            context = self._evaluate_rule(db, rule, latest_tick, portfolio)
            if context is None:
                continue
            if not self._cooldown_passed(rule):
                continue
            event = await self._record_and_send(db, context)
            events.append(event)
        return events

    def _cooldown_passed(self, rule: AlertRule) -> bool:
        if rule.last_triggered_at is None:
            return True
        last = ensure_aware_utc(rule.last_triggered_at)
        return utc_now() - last >= timedelta(seconds=rule.cooldown_seconds or 0)

    def _evaluate_rule(
        self,
        db: Session,
        rule: AlertRule,
        latest_tick: PriceTick,
        portfolio: object,
    ) -> TriggerContext | None:
        price = Decimal(latest_tick.price)
        rule_type = rule.type.upper()
        if rule_type == "PRICE_ABOVE" and rule.target_price is not None:
            target = Decimal(rule.target_price)
            if price >= target:
                message = build_price_alert_text(
                    title="金价守望提醒：价格突破目标价",
                    current_price=price,
                    rule_description=f"当前价格已高于 {format_decimal(target)} 元/克",
                    portfolio=portfolio,
                )
                return TriggerContext(rule=rule, message=message, price=price)
        if rule_type == "PRICE_BELOW" and rule.target_price is not None:
            target = Decimal(rule.target_price)
            if price <= target:
                message = build_price_alert_text(
                    title="金价守望提醒：价格跌破目标价",
                    current_price=price,
                    rule_description=f"当前价格已低于 {format_decimal(target)} 元/克",
                    portfolio=portfolio,
                )
                return TriggerContext(rule=rule, message=message, price=price)
        if rule_type in {"POSITION_GAIN_PERCENT", "POSITION_LOSS_PERCENT"}:
            return self._evaluate_position_percent(rule, price, portfolio)
        if rule_type in {"VOLATILITY_PERCENT", "VOLATILITY_AMOUNT", "WINDOW_RANGE_AMOUNT"}:
            return self._evaluate_volatility(db, rule, latest_tick, portfolio)
        if rule_type == "RANGE_STEP_AMOUNT":
            return self._evaluate_range_steps(db, rule, latest_tick, portfolio)
        return None

    def _evaluate_position_percent(
        self, rule: AlertRule, price: Decimal, portfolio: object
    ) -> TriggerContext | None:
        if portfolio.average_price <= 0 or rule.target_percent is None:
            return None
        change = (price - portfolio.average_price) / portfolio.average_price * Decimal("100")
        target = Decimal(rule.target_percent)
        if rule.type.upper() == "POSITION_GAIN_PERCENT" and change >= target:
            message = build_price_alert_text(
                title="金价守望提醒：持仓涨幅达标",
                current_price=price,
                rule_description=f"当前价较持仓均价上涨 {format_decimal(change)}%，已达到 {format_decimal(target)}%",
                portfolio=portfolio,
            )
            return TriggerContext(rule=rule, message=message, price=price)
        if rule.type.upper() == "POSITION_LOSS_PERCENT" and change <= -target:
            message = build_price_alert_text(
                title="金价守望提醒：持仓跌幅达标",
                current_price=price,
                rule_description=f"当前价较持仓均价下跌 {format_decimal(abs(change))}%，已达到 {format_decimal(target)}%",
                portfolio=portfolio,
            )
            return TriggerContext(rule=rule, message=message, price=price)
        return None

    def _window_ticks(self, db: Session, latest_tick: PriceTick, window_seconds: int) -> list[PriceTick]:
        start = ensure_aware_utc(latest_tick.fetched_at) - timedelta(seconds=window_seconds)
        return db.scalars(
            select(PriceTick)
            .where(PriceTick.fetched_at >= start)
            .order_by(PriceTick.fetched_at.asc(), PriceTick.id.asc())
        ).all()

    def _evaluate_volatility(
        self,
        db: Session,
        rule: AlertRule,
        latest_tick: PriceTick,
        portfolio: object,
    ) -> TriggerContext | None:
        window_seconds = rule.window_seconds or 300
        ticks = self._window_ticks(db, latest_tick, window_seconds)
        if len(ticks) < 2:
            return None
        first = Decimal(ticks[0].price)
        latest = Decimal(latest_tick.price)
        prices = [Decimal(tick.price) for tick in ticks]
        high = max(prices)
        low = min(prices)
        price_range = high - low
        rule_type = rule.type.upper()

        if rule_type == "VOLATILITY_PERCENT" and rule.target_percent is not None and first > 0:
            change_percent = abs(latest - first) / first * Decimal("100")
            if change_percent >= Decimal(rule.target_percent):
                direction = "快速上涨" if latest >= first else "快速下跌"
                message = build_price_alert_text(
                    title=f"金价守望提醒：{direction}",
                    current_price=latest,
                    rule_description=f"近 {window_seconds // 60} 分钟涨跌幅达到 {format_decimal(change_percent)}%",
                    portfolio=portfolio,
                )
                return TriggerContext(rule=rule, message=message, price=latest)
        if rule_type == "VOLATILITY_AMOUNT" and rule.target_amount is not None:
            amount = abs(latest - first)
            if amount >= Decimal(rule.target_amount):
                direction = "快速上涨" if latest >= first else "快速下跌"
                message = build_price_alert_text(
                    title=f"金价守望提醒：{direction}",
                    current_price=latest,
                    rule_description=f"近 {window_seconds // 60} 分钟价格变化 {format_decimal(amount)} 元/克",
                    portfolio=portfolio,
                )
                return TriggerContext(rule=rule, message=message, price=latest)
        if rule_type == "WINDOW_RANGE_AMOUNT" and rule.target_amount is not None:
            if price_range >= Decimal(rule.target_amount):
                direction = "短时拉升" if latest >= (high + low) / 2 else "短时回落"
                message = build_price_alert_text(
                    title=f"金价守望提醒：{direction}",
                    current_price=latest,
                    rule_description=f"近 {window_seconds // 60} 分钟最高最低价差达到 {format_decimal(price_range)} 元/克",
                    portfolio=portfolio,
                    extra_lines=[
                        f"窗口最高价：{format_decimal(high)} 元/克",
                        f"窗口最低价：{format_decimal(low)} 元/克",
                    ],
                )
                return TriggerContext(
                    rule=rule,
                    message=message,
                    price=latest,
                    window_high=high,
                    window_low=low,
                    window_range=price_range,
                )
        return None

    def _evaluate_range_steps(
        self,
        db: Session,
        rule: AlertRule,
        latest_tick: PriceTick,
        portfolio: object,
    ) -> TriggerContext | None:
        if rule.target_price is None or rule.target_amount is None:
            return None
        base_price = Decimal(rule.target_price)
        step_amount = Decimal(rule.target_amount)
        if step_amount <= 0:
            return None

        ticks = db.scalars(
            select(PriceTick).order_by(PriceTick.fetched_at.desc(), PriceTick.id.desc()).limit(2)
        ).all()
        if len(ticks) < 2:
            return None

        latest = Decimal(latest_tick.price)
        previous = Decimal(ticks[1].price)
        latest_index = self._step_index(latest, base_price, step_amount)
        state = self._parse_state(rule.state)

        if previous == latest:
            if state.get("last_step_index") != latest_index:
                state["last_step_index"] = latest_index
            return TriggerContext(
                rule=rule,
                message="",
                price=latest,
                state=state,
            ) if state != self._parse_state(rule.state) else None

        crossed = self._crossed_ladder_prices(previous, latest, base_price, step_amount)
        if not crossed:
            if state.get("last_step_index") != latest_index:
                state["last_step_index"] = latest_index
            return TriggerContext(
                rule=rule,
                message="",
                price=latest,
                state=state,
            ) if state != self._parse_state(rule.state) else None

        crossed_price = crossed[-1]
        crossed_index = self._step_index(crossed_price, base_price, step_amount)
        direction = "向上穿越" if latest > previous else "向下穿越"
        state["last_step_index"] = latest_index
        state["last_crossed_price"] = str(crossed_price)
        message = build_price_alert_text(
            title=f"金价守望提醒：{direction}阶梯价位",
            current_price=latest,
            rule_description=(
                f"价格已{direction} {format_decimal(crossed_price)} 元/克"
                f"（基准 {format_decimal(base_price)}，每 {format_decimal(step_amount)} 元一档）"
            ),
            portfolio=portfolio,
            extra_lines=[
                f"上次价格：{format_decimal(previous)} 元/克",
                f"当前档位：{crossed_index:+d} 档",
                f"本次穿越价位数：{len(crossed)} 个",
            ],
        )
        return TriggerContext(
            rule=rule,
            message=message,
            price=latest,
            triggered_level=crossed_index,
            state=state,
        )

    def _step_index(self, price: Decimal, base_price: Decimal, step_amount: Decimal) -> int:
        return int(((price - base_price) / step_amount).to_integral_value(rounding=ROUND_FLOOR))

    def _crossed_ladder_prices(
        self, previous: Decimal, latest: Decimal, base_price: Decimal, step_amount: Decimal
    ) -> list[Decimal]:
        low = min(previous, latest)
        high = max(previous, latest)
        start_index = self._step_index(low, base_price, step_amount)
        end_index = self._step_index(high, base_price, step_amount)
        candidates = [base_price + step_amount * index for index in range(start_index, end_index + 1)]
        if latest > previous:
            return [price for price in candidates if previous < price <= latest]
        return [price for price in reversed(candidates) if latest <= price < previous]

    def _parse_steps(self, raw: str) -> list[dict[str, Any]]:
        data = json.loads(raw)
        return sorted(data, key=lambda item: Decimal(str(item["amount"])))

    def _parse_state(self, raw: str | None) -> dict[str, Any]:
        if not raw:
            return {"last_step_index": None, "last_crossed_price": None}
        try:
            state = json.loads(raw)
            if not isinstance(state, dict):
                return {"last_step_index": None, "last_crossed_price": None}
            if "last_step_index" not in state and "last_level" in state:
                state = {"last_step_index": None, "last_crossed_price": None}
            return state
        except json.JSONDecodeError:
            return {"last_step_index": None, "last_crossed_price": None}

    async def _record_and_send(self, db: Session, context: TriggerContext) -> AlertEvent:
        rule = context.rule
        if context.state is not None:
            rule.state = json.dumps(context.state, ensure_ascii=False)
        if not context.message:
            rule.updated_at = utc_now()
            db.add(rule)
            db.commit()
            db.refresh(rule)
            return AlertEvent(
                rule_id=rule.id,
                rule_name=rule.name,
                event_type=rule.type,
                price=context.price,
                message="规则状态已更新，未发送通知",
                sent=False,
                created_at=utc_now(),
            )
        result = await self.notifier.send(db, title=rule.name, text=context.message)
        event = AlertEvent(
            rule_id=rule.id,
            rule_name=rule.name,
            event_type=rule.type,
            price=context.price,
            window_high=context.window_high,
            window_low=context.window_low,
            window_range=context.window_range,
            triggered_level=context.triggered_level,
            message=context.message,
            sent=result.sent,
            sent_at=utc_now() if result.sent else None,
            error_message=result.error_message,
            created_at=utc_now(),
        )
        rule.last_triggered_at = utc_now()
        rule.updated_at = utc_now()
        if context.state is not None:
            rule.state = json.dumps(context.state, ensure_ascii=False)
        db.add(event)
        db.add(rule)
        db.commit()
        db.refresh(event)
        return event
