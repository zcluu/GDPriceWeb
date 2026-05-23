from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from datetime import timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.time import utc_now


security_scheme = HTTPBearer(auto_error=False)


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def hash_password(password: str, *, iterations: int = 260_000) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return (
        f"pbkdf2_sha256${iterations}$"
        f"{_b64url_encode(salt)}${_b64url_encode(digest)}"
    )


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return hmac.compare_digest(password, settings.app_password)
    try:
        algorithm, iterations_raw, salt_raw, expected_raw = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_raw)
        salt = _b64url_decode(salt_raw)
        expected = _b64url_decode(expected_raw)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, iterations
        )
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def create_access_token(subject: str = "single-user") -> str:
    now = int(time.time())
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + int(timedelta(minutes=settings.jwt_expire_minutes).total_seconds()),
        "jti": str(uuid.uuid4()),
    }
    header = {"alg": "HS256", "typ": "JWT"}
    header_raw = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_raw = _b64url_encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )
    signing_input = f"{header_raw}.{payload_raw}".encode("ascii")
    signature = hmac.new(
        settings.app_secret_key.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()
    return f"{header_raw}.{payload_raw}.{_b64url_encode(signature)}"


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        header_raw, payload_raw, signature_raw = token.split(".", 2)
        signing_input = f"{header_raw}.{payload_raw}".encode("ascii")
        expected_signature = hmac.new(
            settings.app_secret_key.encode("utf-8"), signing_input, hashlib.sha256
        ).digest()
        actual_signature = _b64url_decode(signature_raw)
        if not hmac.compare_digest(expected_signature, actual_signature):
            raise ValueError("bad signature")
        payload = json.loads(_b64url_decode(payload_raw))
        if int(payload.get("exp", 0)) < int(time.time()):
            raise ValueError("expired token")
        if payload.get("sub") != "single-user":
            raise ValueError("bad subject")
        return payload
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录已失效，请重新登录",
        ) from exc


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录",
        )
    return decode_access_token(credentials.credentials)


def token_expire_at_iso(token: str) -> str:
    payload = decode_access_token(token)
    return utc_now().fromtimestamp(payload["exp"], tz=timezone.utc).isoformat()
