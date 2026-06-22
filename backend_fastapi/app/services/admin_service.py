from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BizError
from app.integrations.object_storage import get_object_storage
from app.models.admin import AuditLog, InviteCode, ModelProviderConfig, RateLimitConfig, RechargeOrder, RechargePackage
from app.models.chat import Conversation, ConversationSession, Generation
from app.models.document import Document
from app.models.user import OrgTag, User, UserOrgTag, UserTokenRecord
from app.services.user_service import serialize_user


def list_users(db: Session) -> list[dict]:
    return [serialize_user(user) for user in db.scalars(select(User).order_by(User.id)).all()]


def create_admin_user(db: Session, username: str, password_hash: str) -> dict:
    """创建管理员账号，供系统初始化后由已有管理员扩展后台用户。"""
    if db.scalar(select(User).where(User.username == username)):
        raise BizError("用户名已存在", 400)
    user = User(username=username, password_hash=password_hash, role="ADMIN", primary_org="default")
    db.add(user)
    db.commit()
    db.refresh(user)
    return serialize_user(user)


def upsert_org_tag(db: Session, tag_id: str, name: str, description: str, parent_tag: str | None, upload_max_size_bytes: int) -> dict:
    """创建或更新组织标签，组织标签是文档权限隔离的核心维度。"""
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


def build_org_tree(orgs: list[OrgTag]) -> list[dict]:
    """将平铺组织标签组装成前端树结构。"""
    nodes = [{**serialize_org_tag(org), "children": []} for org in orgs]
    node_by_id = {node["tagId"]: node for node in nodes}
    roots: list[dict] = []
    for org, node in zip(orgs, nodes):
        parent = node_by_id.get(org.parent_tag or "")
        # 父级不存在时作为根节点返回，避免脏数据导致组织树整支丢失。
        if parent:
            parent["children"].append(node)
        else:
            roots.append(node)
    return roots


def list_invite_codes(db: Session) -> list[dict]:
    return [serialize_invite_code(row) for row in db.scalars(select(InviteCode).order_by(InviteCode.id.desc())).all()]


def upsert_invite_code(db: Session, code: str, max_uses: int, enabled: bool, admin_user: User) -> dict:
    row = db.scalar(select(InviteCode).where(InviteCode.code == code))
    if not row:
        row = InviteCode(code=code, max_uses=max_uses, enabled=enabled, created_by=admin_user.id)
        db.add(row)
    else:
        row.max_uses = max_uses
        row.enabled = enabled
    db.commit()
    db.refresh(row)
    return serialize_invite_code(row)


def serialize_invite_code(row: InviteCode) -> dict:
    return {"id": row.id, "code": row.code, "maxUses": row.max_uses, "usedCount": row.used_count, "enabled": row.enabled, "expiresAt": row.expires_at.isoformat() if row.expires_at else None}


def upsert_rate_limit(db: Session, key: str, payload, admin_user: User) -> dict:
    """更新限流配置，updated_by 用于追踪最后一次调整该策略的管理员。"""
    row = db.get(RateLimitConfig, key)
    if not row:
        row = RateLimitConfig(config_key=key)
        db.add(row)
    row.single_max = payload.singleMax
    row.single_window_seconds = payload.singleWindowSeconds
    row.minute_max = payload.minuteMax
    row.minute_window_seconds = payload.minuteWindowSeconds
    row.day_max = payload.dayMax
    row.day_window_seconds = payload.dayWindowSeconds
    row.updated_by = admin_user.id
    db.commit()
    return {"configKey": row.config_key, "singleMax": row.single_max, "minuteMax": row.minute_max, "dayMax": row.day_max}


def upsert_model_provider(db: Session, payload, admin_user: User) -> dict:
    """保存模型供应商配置。

    同一 scope 只能有一个 active provider；新的 active 配置会自动关闭同 scope 其他配置。
    """
    row = db.scalar(select(ModelProviderConfig).where(ModelProviderConfig.scope == payload.scope, ModelProviderConfig.provider_code == payload.provider))
    if not row:
        row = ModelProviderConfig(scope=payload.scope, provider_code=payload.provider, display_name=payload.displayName)
        db.add(row)
    row.display_name = payload.displayName
    row.api_style = payload.apiStyle
    row.api_base_url = payload.apiBaseUrl
    row.model_name = payload.model
    if payload.apiKey:
        row.api_key_ciphertext = payload.apiKey
    row.embedding_dimension = payload.dimension
    row.enabled = payload.enabled
    row.active = payload.active
    row.updated_by = admin_user.id
    if payload.active:
        for other in db.scalars(select(ModelProviderConfig).where(ModelProviderConfig.scope == payload.scope, ModelProviderConfig.provider_code != payload.provider)).all():
            other.active = False
    db.commit()
    db.refresh(row)
    return serialize_model_provider(row)


def model_provider_settings(db: Session) -> dict:
    rows = db.scalars(select(ModelProviderConfig)).all()
    result = {}
    for scope in ["llm", "embedding"]:
        providers = [serialize_model_provider(row) for row in rows if row.scope == scope]
        active = next((item["provider"] for item in providers if item["active"]), None)
        result[scope] = {"scope": scope, "activeProvider": active, "providers": providers}
    return result


def serialize_model_provider(row: ModelProviderConfig) -> dict:
    masked = "******" if row.api_key_ciphertext else ""
    return {"provider": row.provider_code, "displayName": row.display_name, "apiStyle": row.api_style, "apiBaseUrl": row.api_base_url, "model": row.model_name, "dimension": row.embedding_dimension, "enabled": row.enabled, "active": row.active, "hasApiKey": bool(row.api_key_ciphertext), "maskedApiKey": masked}


def assign_user_orgs(db: Session, user_id: int, org_tags: list[str], primary_org: str) -> None:
    """为用户重新分配组织标签，并校验主组织必须在授权范围内。"""
    user = db.get(User, user_id)
    if not user:
        raise BizError("用户不存在", 404)
    if primary_org not in org_tags:
        raise BizError("主组织必须包含在组织标签列表中", 400)
    existing_orgs = {row.tag_id for row in db.scalars(select(OrgTag).where(OrgTag.tag_id.in_(org_tags))).all()}
    missing = set(org_tags) - existing_orgs
    if missing:
        raise BizError(f"组织标签不存在: {','.join(sorted(missing))}", 400)
    db.query(UserOrgTag).filter(UserOrgTag.user_id == user_id).delete()
    for tag in org_tags:
        db.add(UserOrgTag(user_id=user_id, tag_id=tag))
    user.primary_org = primary_org
    db.commit()


def write_audit_log(db: Session, actor: User | None, action: str, target_type: str, target_id: str = "", detail: str = "") -> None:
    """记录后台高危或运维操作审计日志，调用方负责在同一事务中提交。"""
    db.add(AuditLog(actor_user_id=actor.id if actor else None, action=action, target_type=target_type, target_id=target_id, detail=detail))
    db.flush()


def list_audit_logs(db: Session) -> list[dict]:
    rows = db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(100)).all()
    return [
        {
            "id": row.id,
            "actorUserId": row.actor_user_id,
            "action": row.action,
            "targetType": row.target_type,
            "targetId": row.target_id,
            "detail": row.detail,
            "createdAt": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


def list_admin_conversations(db: Session) -> list[dict]:
    rows = db.scalars(select(ConversationSession).order_by(ConversationSession.updated_at.desc())).all()
    return [
        {
            "id": row.id,
            "userId": row.user_id,
            "conversationId": row.conversation_id,
            "title": row.title,
            "status": row.status,
            "createdAt": row.created_at.isoformat() if row.created_at else None,
            "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
        }
        for row in rows
    ]


def migrate_documents_to_minio(db: Session, actor: User) -> dict:
    """把旧版本存于数据库的文档正文补写入 MinIO，用于平滑迁移对象存储。"""
    storage = get_object_storage()
    migrated = 0
    for doc in db.scalars(select(Document).where(Document.deleted.is_(False))).all():
        if not doc.content:
            continue
        storage.put_bytes(doc.object_key, doc.content.encode("utf-8"), "application/octet-stream")
        migrated += 1
    write_audit_log(db, actor, "MINIO_MIGRATE", "documents", detail=f"migrated={migrated}")
    db.commit()
    return {"migrated": migrated}


def cleanup_all_data(db: Session, actor: User, confirm_text: str) -> dict:
    """清理核心业务数据；该方法只允许在显式开启高危开关后执行。"""
    if not settings.admin_dangerous_operations_enabled:
        raise BizError("高危操作未启用", 403)
    if confirm_text != "CONFIRM_CLEANUP_ALL":
        raise BizError("确认文本不正确", 400)
    write_audit_log(db, actor, "CLEANUP_ALL", "system", detail="cleanup requested")
    deleted = {
        "generations": db.query(Generation).delete(),
        "conversations": db.query(Conversation).delete(),
        "conversationSessions": db.query(ConversationSession).delete(),
        "documents": db.query(Document).delete(),
    }
    db.commit()
    return {"deleted": deleted}


def grant_tokens(db: Session, user_id: int, token_type: str, amount: int, reason: str) -> None:
    """管理员增发用户 token，并写入余额变更账本。"""
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
