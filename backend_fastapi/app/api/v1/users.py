from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.responses import ok
from app.models.user import User, UserTokenRecord
from app.schemas.user import LoginRequest, PrimaryOrgRequest, RegisterRequest
from app.services.user_service import (
    get_org_info,
    login_user,
    register_user,
    serialize_user,
    set_primary_org,
    usage_view,
)
from app.services.rate_limiter import enforce_rate_limit

router = APIRouter()


def _request_identity(request: Request, fallback: str = "unknown") -> str:
    # 测试和反向代理场景可显式传入客户端标识，生产环境默认使用连接 IP。
    return request.headers.get("X-Test-Client") or (request.client.host if request.client else fallback)


@router.post("/register")
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    enforce_rate_limit(db, "register", _request_identity(request))
    register_user(db, payload.username, payload.password, payload.inviteCode)
    return ok(None)


@router.post("/login")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    enforce_rate_limit(db, "login", _request_identity(request, payload.username))
    return ok(login_user(db, payload.username, payload.password))


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return ok(serialize_user(current_user))


@router.get("/org-tags")
def org_tags(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(get_org_info(db, current_user))


@router.put("/primary-org")
def primary_org(payload: PrimaryOrgRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    set_primary_org(db, current_user, payload.primaryOrg)
    return ok(None)


@router.get("/usage")
def usage(current_user: User = Depends(get_current_user)):
    return ok(usage_view(current_user))


@router.get("/upload-orgs")
def upload_orgs(current_user: User = Depends(get_current_user)):
    return ok({"orgTags": [item.tag_id for item in current_user.org_tags], "primaryOrg": current_user.primary_org})


@router.post("/logout")
def logout():
    # 当前阶段 access token 无服务端会话，前端丢弃 token 即可；后续接 Redis 黑名单。
    return ok(None)


@router.post("/logout-all")
def logout_all(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.token_version += 1
    db.commit()
    return ok(None)


@router.get("/token-records")
def token_records(
    page: int = Query(0, ge=0),
    size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(UserTokenRecord).where(UserTokenRecord.user_id == current_user.id).order_by(UserTokenRecord.id.desc())
    records = db.scalars(stmt.offset(page * size).limit(size)).all()
    total = len(db.scalars(select(UserTokenRecord).where(UserTokenRecord.user_id == current_user.id)).all())
    total_pages = (total + size - 1) // size
    content = [
        {
            "id": item.id,
            "recordDate": item.record_date.isoformat(),
            "tokenType": item.token_type,
            "changeType": item.change_type,
            "requestCount": item.request_count,
            "amount": item.amount,
            "balanceBefore": item.balance_before,
            "balanceAfter": item.balance_after,
            "reason": item.reason,
            "remark": item.remark,
            "createdAt": item.created_at.isoformat() if item.created_at else None,
        }
        for item in records
    ]
    return ok(
        {
            "content": content,
            "totalElements": total,
            "totalPages": total_pages,
            "number": page,
            "size": size,
            "first": page == 0,
            "last": page + 1 >= total_pages,
            "empty": total == 0,
        }
    )
