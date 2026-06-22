from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BizError
from app.core.security import create_token, hash_password, verify_password
from app.models.user import OrgTag, User, UserOrgTag, UserTokenRecord


def ensure_default_org(db: Session) -> OrgTag:
    org = db.get(OrgTag, settings.default_org_tag)
    if org:
        return org
    org = OrgTag(tag_id=settings.default_org_tag, name=settings.default_org_name, description="系统默认组织")
    db.add(org)
    db.flush()
    return org


def serialize_user(user: User) -> dict:
    org_tags = [item.tag_id for item in user.org_tags]
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "orgTags": org_tags,
        "primaryOrg": user.primary_org,
        "createdAt": user.created_at.isoformat() if user.created_at else None,
        "updatedAt": user.updated_at.isoformat() if user.updated_at else None,
    }


def issue_tokens(user: User) -> dict:
    token = create_token(str(user.id), "access", user.token_version, timedelta(minutes=settings.access_token_minutes))
    refresh_token = create_token(str(user.id), "refresh", user.token_version, timedelta(days=settings.refresh_token_days))
    return {"token": token, "refreshToken": refresh_token}


def register_user(db: Session, username: str, password: str, invite_code: str | None = None) -> None:
    mode = settings.registration_mode.upper()
    if mode == "CLOSED":
        raise BizError("注册已关闭", 400)
    if mode == "INVITE_ONLY" and not invite_code:
        raise BizError("邀请码不能为空", 400)
    if db.scalar(select(User).where(User.username == username)):
        raise BizError("用户名已存在", 400)

    org = ensure_default_org(db)
    user = User(
        username=username,
        password_hash=hash_password(password),
        primary_org=org.tag_id,
        llm_token_balance=settings.initial_llm_tokens,
        embedding_token_balance=settings.initial_embedding_tokens,
    )
    db.add(user)
    db.flush()
    db.add(UserOrgTag(user_id=user.id, tag_id=org.tag_id))
    _record_initial_tokens(db, user, "LLM", settings.initial_llm_tokens)
    _record_initial_tokens(db, user, "EMBEDDING", settings.initial_embedding_tokens)
    db.commit()


def _record_initial_tokens(db: Session, user: User, token_type: str, amount: int) -> None:
    db.add(
        UserTokenRecord(
            user_id=user.id,
            record_date=date.today(),
            token_type=token_type,
            change_type="INCREASE",
            amount=amount,
            balance_before=0,
            balance_after=amount,
            reason="初始化额度",
        )
    )


def consume_user_tokens(db: Session, user: User, token_type: str, amount: int, reason: str, remark: str = "") -> None:
    if token_type == "LLM":
        before = user.llm_token_balance
        if before < amount:
            raise BizError("LLM token 额度不足", 400)
        user.llm_token_balance -= amount
        after = user.llm_token_balance
    elif token_type == "EMBEDDING":
        before = user.embedding_token_balance
        if before < amount:
            raise BizError("Embedding token 额度不足", 400)
        user.embedding_token_balance -= amount
        after = user.embedding_token_balance
    else:
        raise BizError("token 类型不正确", 400)
    db.add(
        UserTokenRecord(
            user_id=user.id,
            record_date=date.today(),
            token_type=token_type,
            change_type="CONSUME",
            amount=amount,
            balance_before=before,
            balance_after=after,
            reason=reason,
            remark=remark,
        )
    )


def login_user(db: Session, username: str, password: str) -> dict:
    user = db.scalar(select(User).where(User.username == username))
    if not user or not verify_password(password, user.password_hash):
        raise BizError("用户名或密码错误", 401)
    if not user.enabled:
        raise BizError("用户已禁用", 403)
    return issue_tokens(user)


def get_org_info(db: Session, user: User) -> dict:
    tag_ids = [item.tag_id for item in user.org_tags]
    orgs = db.scalars(select(OrgTag).where(OrgTag.tag_id.in_(tag_ids))).all() if tag_ids else []
    return {
        "orgTags": tag_ids,
        "primaryOrg": user.primary_org,
        "orgTagDetails": [
            {"tagId": org.tag_id, "name": org.name, "description": org.description} for org in orgs
        ],
    }


def set_primary_org(db: Session, user: User, primary_org: str) -> None:
    owned = {item.tag_id for item in user.org_tags}
    if primary_org not in owned:
        raise BizError("主组织必须属于当前用户已绑定的组织", 400)
    user.primary_org = primary_org
    db.commit()


def usage_view(user: User) -> dict:
    return {
        "day": date.today().isoformat(),
        "chatRequestCount": 0,
        "llm": {
            "enabled": True,
            "usedTokens": 0,
            "limitTokens": user.llm_token_balance,
            "remainingTokens": user.llm_token_balance,
            "requestCount": 0,
        },
        "embedding": {
            "enabled": True,
            "usedTokens": 0,
            "limitTokens": user.embedding_token_balance,
            "remainingTokens": user.embedding_token_balance,
            "requestCount": 0,
        },
    }
