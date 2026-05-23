from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import settings
from app.core.security import create_access_token, get_current_user, verify_password
from app.schemas.auth import LoginRequest, MeResponse, TokenResponse


router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    if not verify_password(payload.password, settings.app_password_hash):
        raise HTTPException(status_code=401, detail="密码错误")
    return TokenResponse(
        access_token=create_access_token(),
        expires_in_minutes=settings.jwt_expire_minutes,
    )


@router.post("/logout")
def logout(_: dict = Depends(get_current_user)) -> dict[str, str]:
    return {"message": "已退出登录"}


@router.get("/me", response_model=MeResponse)
def me(_: dict = Depends(get_current_user)) -> MeResponse:
    return MeResponse()

