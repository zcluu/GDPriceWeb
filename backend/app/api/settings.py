from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.settings import SettingsResponse, SettingsUpdate
from app.services.settings_service import get_public_settings, set_setting


router = APIRouter(prefix="/settings", tags=["设置"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=SettingsResponse)
def read_settings(db: Session = Depends(get_db)) -> dict[str, object]:
    return get_public_settings(db)


@router.put("", response_model=SettingsResponse)
def update_settings(payload: SettingsUpdate, db: Session = Depends(get_db)) -> dict[str, object]:
    mapping = {
        "refresh_interval_seconds": payload.refresh_interval_seconds,
        "history_retention_days": payload.history_retention_days,
        "default_chart_interval_seconds": payload.default_chart_interval_seconds,
        "market_visualization_window_hours": payload.market_visualization_window_hours,
        "accumulation_gold_trading_hours_enabled": payload.accumulation_gold_trading_hours_enabled,
        "trading_timezone": payload.trading_timezone,
        "dingtalk_enabled": payload.dingtalk_enabled,
        "dingtalk_webhook": payload.dingtalk_webhook,
        "dingtalk_secret": payload.dingtalk_secret,
        "dingtalk_message_style": payload.dingtalk_message_style,
        "default_alert_cooldown_seconds": payload.default_alert_cooldown_seconds,
        "default_range_window_seconds": payload.default_range_window_seconds,
        "default_range_steps": payload.default_range_steps,
        "rise_color": payload.rise_color,
        "fall_color": payload.fall_color,
    }
    for key, value in mapping.items():
        if value is None:
            continue
        set_setting(db, key, str(value).lower() if isinstance(value, bool) else str(value))
    db.commit()
    return get_public_settings(db)
