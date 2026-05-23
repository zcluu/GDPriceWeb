from __future__ import annotations

import base64
import hashlib
import hmac
import time
import urllib.parse
from dataclasses import dataclass
from decimal import Decimal
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.time import utc_now
from app.db.models import AlertRule, PriceTick
from app.services.settings_service import get_bool_setting, get_setting


@dataclass
class NotificationResult:
    sent: bool
    error_message: str | None = None


class DingTalkNotifier:
    def build_frontend_url(self, path: str = "/dashboard") -> str:
        base_url = settings.app_public_url.strip().rstrip("/")
        path = path if path.startswith("/") else f"/{path}"
        return f"{base_url}{path}"

    def build_action_url(self, action: str) -> str:
        return self.build_frontend_url(f"/dashboard?ding_action={urllib.parse.quote(action)}")

    def build_signed_url(self, webhook: str, secret: str) -> str:
        if not secret:
            return webhook
        timestamp = str(round(time.time() * 1000))
        string_to_sign = f"{timestamp}\n{secret}"
        digest = hmac.new(
            secret.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha256
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(digest))
        separator = "&" if "?" in webhook else "?"
        return f"{webhook}{separator}timestamp={timestamp}&sign={sign}"

    def build_action_card_payload(
        self,
        *,
        title: str,
        text: str,
        button_url: str = "",
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "msgtype": "actionCard",
            "actionCard": {
                "title": title,
                "text": text,
                "btnOrientation": "0",
                "singleTitle": "打开金价守望",
                "singleURL": button_url or self.build_frontend_url("/dashboard"),
            },
        }
        return payload

    def build_interactive_payload(
        self,
        *,
        title: str,
        text: str,
        db: Session,
    ) -> dict[str, object]:
        summary_lines = self._market_summary_lines(db)
        rules = db.scalars(select(AlertRule).order_by(AlertRule.id.asc())).all()
        rule_lines = [
            f"- {rule.name}：{'启用' if rule.enabled else '停用'}"
            for rule in rules
        ] or ["- 暂无提醒规则"]
        card_text = "\n\n".join(
            [
                text,
                "",
                "### 当前行情",
                *summary_lines,
                "",
                "### 提醒规则",
                *rule_lines,
            ]
        )
        return {
            "msgtype": "actionCard",
            "actionCard": {
                "title": title,
                "text": card_text,
                "btnOrientation": "1",
                "btns": [
                    {"title": "打开看板", "actionURL": self.build_frontend_url("/dashboard")},
                    {"title": "查看规则", "actionURL": self.build_frontend_url("/alerts")},
                    {"title": "暂停提醒", "actionURL": self.build_action_url("disable_dingtalk")},
                    {"title": "恢复提醒", "actionURL": self.build_action_url("enable_dingtalk")},
                ],
            },
        }

    def build_markdown_payload(self, *, title: str, text: str) -> dict[str, object]:
        return {
            "msgtype": "markdown",
            "markdown": {"title": title, "text": text},
        }

    async def send(self, db: Session, *, title: str, text: str) -> NotificationResult:
        enabled = get_bool_setting(db, "dingtalk_enabled", False)
        webhook = get_setting(db, "dingtalk_webhook", "")
        secret = get_setting(db, "dingtalk_secret", "")
        style = get_setting(db, "dingtalk_message_style", "standard")
        if not enabled:
            return NotificationResult(sent=False, error_message="钉钉通知未启用")
        if not webhook:
            return NotificationResult(sent=False, error_message="钉钉 Webhook 未配置")

        url = self.build_signed_url(webhook, secret)
        payload = (
            self.build_interactive_payload(title=title, text=text, db=db)
            if style in {"standard", "detailed", "detail", "详细", "标准"}
            else self.build_markdown_payload(title=title, text=text)
        )
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                if data.get("errcode", 0) != 0:
                    return NotificationResult(
                        sent=False,
                        error_message=f"钉钉返回错误：{data}",
                    )
            return NotificationResult(sent=True)
        except Exception as exc:
            return NotificationResult(sent=False, error_message=str(exc))

    def _market_summary_lines(self, db: Session) -> list[str]:
        ticks = list(
            db.scalars(
                select(PriceTick).order_by(PriceTick.fetched_at.desc(), PriceTick.id.desc()).limit(2)
            ).all()
        )
        if not ticks:
            return ["- 当前金价：暂无", "- 涨跌幅：暂无", "- 今日最高：暂无", "- 今日最低：暂无"]
        latest = Decimal(ticks[0].price)
        previous = Decimal(ticks[1].price) if len(ticks) > 1 else None
        change_percent = (
            (latest - previous) / previous * Decimal("100")
            if previous is not None and previous > 0
            else None
        )
        timezone_name = get_setting(db, "trading_timezone", settings.trading_timezone)
        now = utc_now().astimezone(ZoneInfo(timezone_name))
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(ZoneInfo("UTC"))
        today_prices = [
            Decimal(tick.price)
            for tick in db.scalars(select(PriceTick).where(PriceTick.fetched_at >= day_start)).all()
        ]
        return [
            f"- 当前金价：{format_decimal(latest)} 元/克",
            f"- 涨跌幅：{format_decimal(change_percent)}%",
            f"- 今日最高：{format_decimal(max(today_prices) if today_prices else latest)} 元/克",
            f"- 今日最低：{format_decimal(min(today_prices) if today_prices else latest)} 元/克",
        ]


def format_decimal(value: Decimal | None, places: str = "0.01") -> str:
    if value is None:
        return "-"
    return str(Decimal(value).quantize(Decimal(places)))


def build_price_alert_text(
    *,
    title: str,
    current_price: Decimal | None,
    rule_description: str,
    portfolio: object | None,
    source_display_name: str = "京东金融黄金价格",
    extra_lines: list[str] | None = None,
) -> str:
    now = utc_now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"## {title}",
        "",
        f"**当前金价**：{format_decimal(current_price)} 元/克",
        f"**触发规则**：{rule_description}",
        "",
        "### 持仓概览",
    ]
    if portfolio is None:
        lines.extend(["持仓信息：暂无"])
    else:
        lines.extend(
            [
                f"持仓均价：{format_decimal(portfolio.average_price)} 元/克",
                f"持仓克重：{format_decimal(portfolio.holding_grams)} 克",
                f"浮动盈亏：{format_decimal(portfolio.floating_pnl)} 元（{format_decimal(portfolio.floating_pnl_percent)}%）",
            ]
        )
    if extra_lines:
        lines.extend(["", "### 行情信息", *extra_lines])
    lines.extend(["", f"触发时间：{now}", f"数据来源：{source_display_name}"])
    return "\n\n".join(lines)
