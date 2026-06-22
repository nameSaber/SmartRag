from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.exceptions import BizError


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_token(subject: str, token_type: str, token_version: int, expires_delta: timedelta) -> str:
    # jti 用于后续单设备登出和审计扩展。
    payload = {
        "sub": subject,
        "typ": token_type,
        "ver": token_version,
        "jti": str(uuid4()),
        "exp": utc_now() + expires_delta,
        "iat": utc_now(),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: str | None = None) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise BizError("无效或已过期的 token", 401) from exc
    if expected_type and payload.get("typ") != expected_type:
        raise BizError("token 类型不正确", 401)
    return payload

