from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import BizError
from app.core.security import decode_token
from app.models.user import User


def get_current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise BizError("未登录或登录已过期", 401)
    payload = decode_token(authorization.removeprefix("Bearer ").strip(), "access")
    user = db.get(User, int(payload["sub"]))
    if not user or not user.enabled:
        raise BizError("用户不存在或已禁用", 401)
    if int(payload.get("ver", -1)) != user.token_version:
        raise BizError("token 已失效", 401)
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "ADMIN":
        raise BizError("需要管理员权限", 403)
    return current_user

