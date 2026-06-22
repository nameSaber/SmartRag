from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BizError
from app.models.admin import RechargeOrder, RechargePackage
from app.models.user import OrgTag, User, UserOrgTag, UserTokenRecord
from app.services.user_service import serialize_user


def list_users(db: Session) -> list[dict]:
    return [serialize_user(user) for user in db.scalars(select(User).order_by(User.id)).all()]


def create_admin_user(db: Session, username: str, password_hash: str) -> dict:
    if db.scalar(select(User).where(User.username == username)):
        raise BizError("用户名已存在", 400)
    user = User(username=username, password_hash=password_hash, role="ADMIN", primary_org="default")
    db.add(user)
    db.commit()
    db.refresh(user)
    return serialize_user(user)


def upsert_org_tag(db: Session, tag_id: str, name: str, description: str, parent_tag: str | None, upload_max_size_bytes: int) -> dict:
    org = db.get(OrgTag, tag_id)
    if not org:
        org = OrgTag(tag_id=tag_id, name=name, description=description, parent_tag=parent_tag, upload_max_size_bytes=upload_max_size_bytes)
        db.add(org)
    else:
        org.name = name
        org.description = description
        org.parent_tag = parent_tag
        org.upload_max_size_bytes = upload_max_size_bytes
    db.commit()
    return serialize_org_tag(org)


def serialize_org_tag(org: OrgTag) -> dict:
    return {
        "tagId": org.tag_id,
        "name": org.name,
        "description": org.description,
        "parentTag": org.parent_tag,
        "uploadMaxSizeBytes": org.upload_max_size_bytes,
        "uploadMaxSizeMb": org.upload_max_size_bytes // 1024 // 1024,
    }


def grant_tokens(db: Session, user_id: int, token_type: str, amount: int, reason: str) -> None:
    user = db.get(User, user_id)
    if not user:
        raise BizError("用户不存在", 404)
    if token_type == "LLM":
        before = user.llm_token_balance
        user.llm_token_balance += amount
        after = user.llm_token_balance
    else:
        before = user.embedding_token_balance
        user.embedding_token_balance += amount
        after = user.embedding_token_balance
    db.add(UserTokenRecord(user_id=user.id, record_date=date.today(), token_type=token_type, change_type="INCREASE", amount=amount, balance_before=before, balance_after=after, reason=reason))
    db.commit()


def ensure_default_package(db: Session) -> None:
    exists = db.scalar(select(RechargePackage).where(RechargePackage.deleted.is_(False)))
    if exists:
        return
    db.add(RechargePackage(package_name="基础套餐", package_price=990, package_desc="默认充值套餐", package_benefit="增加 token 额度", llm_token=10000, embedding_token=10000, enabled=True))
    db.commit()


def list_packages(db: Session) -> list[dict]:
    ensure_default_package(db)
    rows = db.scalars(select(RechargePackage).where(RechargePackage.deleted.is_(False)).order_by(RechargePackage.sort_order, RechargePackage.id)).all()
    return [serialize_package(row) for row in rows]


def create_package(db: Session, **kwargs) -> dict:
    pkg = RechargePackage(
        package_name=kwargs["package_name"],
        package_price=kwargs["package_price"],
        package_desc=kwargs.get("package_desc", ""),
        package_benefit=kwargs.get("package_benefit", ""),
        llm_token=kwargs.get("llm_token", 0),
        embedding_token=kwargs.get("embedding_token", 0),
        enabled=kwargs.get("enabled", True),
        sort_order=kwargs.get("sort_order", 0),
    )
    db.add(pkg)
    db.commit()
    db.refresh(pkg)
    return serialize_package(pkg)


def create_order(db: Session, user: User, package_id: int) -> dict:
    ensure_default_package(db)
    pkg = db.get(RechargePackage, package_id)
    if not pkg or pkg.deleted or not pkg.enabled:
        raise BizError("套餐不存在或不可用", 404)
    order = RechargeOrder(trade_no=f"PS{uuid4().hex}", user_id=user.id, package_id=pkg.id, amount=pkg.package_price, llm_token=pkg.llm_token, embedding_token=pkg.embedding_token, description=pkg.package_name)
    db.add(order)
    db.commit()
    db.refresh(order)
    return serialize_order(order)


def pay_callback(db: Session, trade_no: str, transaction_id: str | None, status: str) -> dict:
    order = db.scalar(select(RechargeOrder).where(RechargeOrder.trade_no == trade_no))
    if not order:
        raise BizError("订单不存在", 404)
    if order.status == "SUCCEED":
        return serialize_order(order)
    order.status = status
    order.wx_transaction_id = transaction_id
    if status == "SUCCEED":
        order.pay_time = datetime.utcnow()
        grant_tokens(db, order.user_id, "LLM", order.llm_token, f"充值到账:{trade_no}")
        grant_tokens(db, order.user_id, "EMBEDDING", order.embedding_token, f"充值到账:{trade_no}")
    db.commit()
    return serialize_order(order)


def serialize_package(pkg: RechargePackage) -> dict:
    return {"id": pkg.id, "packageName": pkg.package_name, "packagePrice": pkg.package_price, "packageDesc": pkg.package_desc, "packageBenefit": pkg.package_benefit, "llmToken": pkg.llm_token, "embeddingToken": pkg.embedding_token, "enabled": pkg.enabled, "sortOrder": pkg.sort_order}


def serialize_order(order: RechargeOrder) -> dict:
    return {"id": order.id, "tradeNo": order.trade_no, "userId": order.user_id, "packageId": order.package_id, "amount": order.amount, "llmToken": order.llm_token, "embeddingToken": order.embedding_token, "status": order.status, "description": order.description, "payTime": order.pay_time.isoformat() if order.pay_time else None}

