from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select

from app.core.config import settings
from app.core.time import utc_now
from app.db.models import AlertEvent, PriceTick
from app.db.session import session_scope
from app.services.alert_engine import AlertEngine
from app.services.candle_service import update_candles_for_tick
from app.services.dingtalk_notifier import DingTalkNotifier
from app.services.price_provider import JDGoldPriceProvider, PriceProviderError
from app.services.settings_service import get_int_setting, get_setting
from app.services.trading_calendar import next_trading_start, should_collect_now
from app.services.websocket_manager import manager

logger = logging.getLogger(__name__)


@dataclass
class CollectorStatus:
    status: str = "idle"
    failed_count: int = 0
    last_error: str | None = None
    last_success_at: datetime | None = None
    next_trading_start_at: datetime | None = None
    running: bool = False


class PriceCollector:
    def __init__(
        self,
        provider: JDGoldPriceProvider | None = None,
        alert_engine: AlertEngine | None = None,
    ) -> None:
        self.provider = provider or JDGoldPriceProvider()
        self.alert_engine = alert_engine or AlertEngine()
        self.status = CollectorStatus()
        self._stop_event = asyncio.Event()

    async def stop(self) -> None:
        self._stop_event.set()

    async def run_forever(self) -> None:
        self.status.running = True
        self.status.status = "running"
        logger.info("金价后台采集器已启动")
        try:
            while not self._stop_event.is_set():
                try:
                    await self.run_once()
                except (TradingClosedError, PriceProviderError):
                    pass
                except Exception:
                    logger.exception("金价采集循环出现未预期异常")
                interval = self._refresh_interval()
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=interval)
                except asyncio.TimeoutError:
                    pass
        finally:
            self.status.running = False
            self.status.status = "stopped"
            logger.info("金价后台采集器已停止")

    def _refresh_interval(self) -> int:
        with session_scope() as db:
            return max(5, min(3600, get_int_setting(db, "refresh_interval_seconds", 30)))

    async def run_once(self) -> PriceTick:
        with session_scope() as db:
            if not should_collect_now(db):
                timezone_name = get_setting(db, "trading_timezone", settings.trading_timezone)
                self.status.status = "paused"
                self.status.last_error = None
                self.status.next_trading_start_at = next_trading_start(
                    utc_now(), timezone_name=timezone_name
                )
                logger.info(
                    "当前不在积存金交易时间内，暂停金价采集，下次开盘时间：%s",
                    self.status.next_trading_start_at,
                )
                raise TradingClosedError("当前不在积存金交易时间内，暂停监控")

        try:
            quote = await self.provider.fetch()
        except PriceProviderError as exc:
            self.status.failed_count += 1
            self.status.status = "error"
            self.status.last_error = str(exc)
            logger.warning("金价采集失败：%s", exc)
            await self._maybe_record_collect_error(str(exc))
            raise

        with session_scope() as db:
            tick = PriceTick(
                source=quote.source,
                price=quote.price,
                fetched_at=quote.fetched_at,
                raw_payload=quote.raw_payload_text(),
                created_at=utc_now(),
            )
            db.add(tick)
            db.flush()
            update_candles_for_tick(db, tick)
            db.commit()
            db.refresh(tick)

            events = await self.alert_engine.evaluate(db, tick)
            self.status.status = "ok"
            self.status.failed_count = 0
            self.status.last_error = None
            self.status.last_success_at = tick.fetched_at
            self.status.next_trading_start_at = None
            await manager.broadcast(
                {
                    "type": "price_tick",
                    "payload": {
                        "price": str(Decimal(tick.price)),
                        "source": tick.source,
                        "fetched_at": tick.fetched_at.isoformat(),
                    },
                }
            )
            for event in events:
                if getattr(event, "id", None):
                    await manager.broadcast(
                        {
                            "type": "alert_event",
                            "payload": {
                                "rule_name": event.rule_name,
                                "message": event.message,
                                "created_at": event.created_at.isoformat(),
                            },
                        }
                    )
            return tick

    async def _maybe_record_collect_error(self, message: str) -> None:
        if self.status.failed_count != 3:
            return
        with session_scope() as db:
            notifier = DingTalkNotifier()
            event = AlertEvent(
                rule_id=None,
                rule_name="金价接口异常",
                event_type="COLLECTOR_ERROR",
                message=f"金价接口连续 3 次抓取失败：{message}",
                sent=False,
                created_at=utc_now(),
            )
            result = await notifier.send(
                db,
                title="金价守望提醒：接口异常",
                text=event.message,
            )
            event.sent = result.sent
            event.sent_at = utc_now() if result.sent else None
            event.error_message = result.error_message
            db.add(event)
            db.commit()


collector = PriceCollector()


def latest_tick_from_db() -> PriceTick | None:
    with session_scope() as db:
        return db.scalar(select(PriceTick).order_by(PriceTick.fetched_at.desc(), PriceTick.id.desc()))


class TradingClosedError(RuntimeError):
    pass
