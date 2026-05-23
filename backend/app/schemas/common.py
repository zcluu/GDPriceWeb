from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, field_serializer

from app.core.time import ensure_aware_utc


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_serializer("*", when_used="json")
    def serialize_specials(self, value: Any) -> Any:
        if isinstance(value, Decimal):
            return str(value.quantize(Decimal("0.0001")).normalize())
        if isinstance(value, datetime):
            return ensure_aware_utc(value).isoformat()
        return value


def decimal_to_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value.quantize(Decimal("0.0001")).normalize())
