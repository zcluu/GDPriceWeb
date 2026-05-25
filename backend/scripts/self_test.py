from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("WATCHGOLD_DISABLE_COLLECTOR", "true")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{(ROOT / 'runtime' / 'self_test.db').as_posix()}")
os.environ.setdefault("APP_SECRET_KEY", "self-test-secret")
os.environ.setdefault("APP_PASSWORD", "admin123")
os.environ.setdefault("ACCUMULATION_GOLD_TRADING_HOURS_ENABLED", "false")

from fastapi.testclient import TestClient  # noqa: E402

from app.core.time import utc_now  # noqa: E402
from app.db.session import reset_database_for_tests  # noqa: E402
from app.main import app  # noqa: E402
from app.services.price_collector import PriceCollector  # noqa: E402
from app.services.price_provider import PriceQuote  # noqa: E402
from app.services.trading_calendar import is_accumulation_gold_trading_time  # noqa: E402


@dataclass
class FakeProvider:
    prices: list[Decimal]
    offset_seconds: int = -240

    async def fetch(self) -> PriceQuote:
        if not self.prices:
            raise RuntimeError("测试价格已用尽")
        price = self.prices.pop(0)
        fetched_at = utc_now() + timedelta(seconds=self.offset_seconds)
        self.offset_seconds += 60
        return PriceQuote(
            source="self_test",
            source_display_name="自测金价数据",
            price=price,
            fetched_at=fetched_at,
            raw_payload={"price": str(price), "source": "self_test"},
        )


class SilentNotifier:
    async def send(self, db, *, title: str, text: str):
        class Result:
            sent = True
            error_message = None

        return Result()


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(
            f"{label} 状态码错误：期望 {expected}，实际 {response.status_code}，响应 {response.text}"
        )


def main() -> None:
    from datetime import datetime, timezone

    assert is_accumulation_gold_trading_time(
        datetime(2026, 5, 18, 0, 59, tzinfo=timezone.utc)
    ) is False  # 周一 08:59 中国时间
    assert is_accumulation_gold_trading_time(
        datetime(2026, 5, 18, 1, 0, tzinfo=timezone.utc)
    ) is True  # 周一 09:00 中国时间
    assert is_accumulation_gold_trading_time(
        datetime(2026, 5, 22, 17, 59, tzinfo=timezone.utc)
    ) is True  # 周六 01:59 中国时间
    assert is_accumulation_gold_trading_time(
        datetime(2026, 5, 22, 18, 0, tzinfo=timezone.utc)
    ) is False  # 周六 02:00 中国时间

    reset_database_for_tests()
    with TestClient(app) as client:
        health = client.get("/api/health")
        assert_status(health, 200, "健康检查")

        public_latest = client.get("/api/market/latest")
        assert_status(public_latest, 200, "未登录访问行情")
        unauthorized_events = client.get("/api/alerts/events")
        assert_status(unauthorized_events, 401, "未登录访问异动")

        login = client.post("/api/auth/login", json={"password": "admin123"})
        assert_status(login, 200, "登录")
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        me = client.get("/api/auth/me", headers=headers)
        assert_status(me, 200, "当前用户")

        settings = client.put(
            "/api/settings",
            headers=headers,
            json={
                "refresh_interval_seconds": 5,
                "dingtalk_enabled": False,
                "default_range_window_seconds": 300,
                "market_visualization_window_hours": 48,
                "accumulation_gold_trading_hours_enabled": False,
            },
        )
        assert_status(settings, 200, "更新设置")
        assert settings.json()["refresh_interval_seconds"] == 5

        create_rule = client.post(
            "/api/alerts/rules",
            headers=headers,
            json={
                "name": "基准 1000 元每 2 元阶梯提醒",
                "type": "RANGE_STEP_AMOUNT",
                "target_price": "1000.00",
                "target_amount": "2.00",
                "trigger_mode": "CROSS_EACH_STEP",
                "cooldown_seconds": 0,
                "enabled": True,
            },
        )
        assert_status(create_rule, 200, "创建阶梯提醒")
        rule_data = create_rule.json()
        assert Decimal(rule_data["target_price"]) == Decimal("1000.0000")
        assert Decimal(rule_data["target_amount"]) == Decimal("2.0000")

        provider = FakeProvider(
            prices=[
                Decimal("999.50"),
                Decimal("1000.20"),
                Decimal("1001.80"),
                Decimal("1002.30"),
                Decimal("1004.10"),
            ]
        )
        collector = PriceCollector(provider=provider)
        collector.alert_engine.notifier = SilentNotifier()
        for _ in range(5):
            asyncio.run(collector.run_once())

        latest = client.get("/api/market/latest", headers=headers)
        assert_status(latest, 200, "最新行情")
        assert Decimal(latest.json()["price"]) == Decimal("1004.1000")
        latest_time = latest.json()["fetched_at"]
        if not (latest_time.endswith("+00:00") or latest_time.endswith("Z")):
            raise AssertionError(f"最新行情时间缺少时区信息：{latest_time}")

        market_status = client.get("/api/market/status", headers=headers)
        assert_status(market_status, 200, "行情状态")
        status_data = market_status.json()
        assert status_data["visualization_window_hours"] == 48
        assert "周一 09:00 至周六 02:00" in status_data["trading_hours_description"]

        market_summary = client.get("/api/market/summary")
        assert_status(market_summary, 200, "公开行情摘要")
        assert Decimal(market_summary.json()["current_price"]) == Decimal("1004.1000")

        minute_averages = client.get("/api/market/minute-averages?limit=10")
        assert_status(minute_averages, 200, "公开每分钟均价")
        average_data = minute_averages.json()
        assert average_data
        assert "average_price" in average_data[0]

        ticks = client.get("/api/market/ticks?limit=10", headers=headers)
        assert_status(ticks, 200, "历史行情")
        assert len(ticks.json()) == 5
        first_tick_time = ticks.json()[0]["fetched_at"]
        if not (first_tick_time.endswith("+00:00") or first_tick_time.endswith("Z")):
            raise AssertionError(f"历史行情时间缺少时区信息：{first_tick_time}")

        narrow_ticks = client.get("/api/market/ticks?limit=10&start=2099-01-01T00:00:00Z", headers=headers)
        assert_status(narrow_ticks, 200, "历史行情显式时间过滤")
        assert narrow_ticks.json() == []

        candles = client.get("/api/candles?interval=300&limit=10", headers=headers)
        assert_status(candles, 200, "分钟线")
        assert len(candles.json()) >= 1

        two_hour_candles = client.get("/api/candles?interval=7200&limit=10")
        assert_status(two_hour_candles, 200, "2 小时分钟线")
        assert len(two_hour_candles.json()) >= 1

        buy = client.post(
            "/api/trades",
            headers=headers,
            json={"side": "BUY", "price": "735.20", "grams": "12.5", "fee": "1.00"},
        )
        assert_status(buy, 200, "买入")

        portfolio = client.get("/api/trades/portfolio", headers=headers)
        assert_status(portfolio, 200, "持仓")
        data = portfolio.json()
        assert Decimal(data["holding_grams"]) == Decimal("12.5000")
        assert Decimal(data["average_price"]) > Decimal("735")

        sell_too_much = client.post(
            "/api/trades",
            headers=headers,
            json={"side": "SELL", "price": "1004.10", "grams": "99", "fee": "0"},
        )
        assert_status(sell_too_much, 400, "超卖校验")

        sell = client.post(
            "/api/trades",
            headers=headers,
            json={"side": "SELL", "price": "1004.10", "grams": "2.5", "fee": "0.50"},
        )
        assert_status(sell, 200, "卖出")

        events = client.get("/api/alerts/events", headers=headers)
        assert_status(events, 200, "提醒事件")
        event_data = events.json()
        step_events = [item for item in event_data if item["event_type"] == "RANGE_STEP_AMOUNT"]
        if not step_events:
            raise AssertionError(f"未找到阶梯价差提醒事件：{event_data}")
        if not any(item["triggered_level"] == 2 for item in step_events):
            raise AssertionError(f"未找到穿越 1004 元的 +2 档阶梯提醒：{step_events}")

        bad_login = client.post("/api/auth/login", json={"password": "wrong"})
        assert_status(bad_login, 401, "错误密码")

    print("后端自测通过：认证、行情、分钟线、交易、持仓、阶梯提醒均正常。")


if __name__ == "__main__":
    main()
