from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.core.config import settings
from app.core.time import utc_now

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PriceQuote:
    source: str
    source_display_name: str
    price: Decimal
    fetched_at: object
    raw_payload: dict[str, Any]

    def raw_payload_text(self) -> str:
        return json.dumps(self.raw_payload, ensure_ascii=False)


class PriceProviderError(RuntimeError):
    pass


class JDGoldPriceProvider:
    source = "jd_gold"
    source_display_name = "京东金融黄金价格"

    def __init__(self, url: str | None = None, timeout_seconds: int | None = None) -> None:
        self.url = url or settings.price_provider_url
        self.timeout_seconds = timeout_seconds or settings.price_request_timeout_seconds

    async def fetch(self) -> PriceQuote:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                response = await client.get(self.url)
                response.raise_for_status()
                payload = response.json()
            except Exception as exc:
                logger.warning("金价接口请求失败: %s", exc)
                raise PriceProviderError(f"金价接口请求失败：{exc}") from exc

        try:
            raw_price = payload["resultData"]["datas"]["price"]
            price = Decimal(str(raw_price))
        except (KeyError, TypeError, InvalidOperation) as exc:
            raise PriceProviderError("金价接口返回结构异常，无法解析价格") from exc

        if price <= 0:
            raise PriceProviderError("金价接口返回了无效价格")

        return PriceQuote(
            source=self.source,
            source_display_name=self.source_display_name,
            price=price,
            fetched_at=utc_now(),
            raw_payload=payload,
        )

