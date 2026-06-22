from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import BizError
from app.core.responses import ok
from app.core.security import decode_token
from app.models.user import User
from app.schemas.user import RefreshTokenRequest
from app.services.user_service import issue_tokens

router = APIRouter()


@router.post("/refreshToken")
def refresh_token(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    decoded = decode_token(payload.refreshToken, "refresh")
    user = db.get(User, int(decoded["sub"]))
    if not user or not user.enabled or int(decoded.get("ver", -1)) != user.token_version:
        raise BizError("refresh token 已失效", 401)
    return ok(issue_tokens(user))


@router.get("/error")
def auth_error():
    raise BizError("认证失败", 401)

