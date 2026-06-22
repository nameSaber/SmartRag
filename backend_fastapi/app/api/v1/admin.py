from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.core.responses import ok
from app.integrations.health import dependency_health
from app.core.security import hash_password
from app.models.admin import RateLimitConfig
from app.models.user import OrgTag, User
from app.schemas.admin import (
    CleanupAllRequest,
    InviteCodeRequest,
    ModelProviderRequest,
    OrgTagUpsertRequest,
    RateLimitConfigRequest,
    RechargePackageRequest,
    TokenGrantRequest,
    UserOrgAssignRequest,
)
from app.schemas.user import RegisterRequest
from app.services.admin_service import (
    assign_user_orgs,
    build_org_tree,
    create_admin_user,
    create_package,
    grant_tokens,
    list_invite_codes,
    list_admin_conversations,
    list_audit_logs,
    list_packages,
    list_users,
    cleanup_all_data,
    migrate_documents_to_minio,
    model_provider_settings,
    serialize_org_tag,
    upsert_invite_code,
    upsert_model_provider,
    upsert_org_tag,
    upsert_rate_limit,
)

router = APIRouter()


@router.get("/users")
def users(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return ok(list_users(db))


@router.post("/admins")
def admins(payload: RegisterRequest, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    return ok(create_admin_user(db, payload.username, hash_password(payload.password)))


@router.get("/status")
def status(_: User = Depends(require_admin)):
    """聚合外部依赖健康状态，供管理后台运维面板展示。"""
    return ok(dependency_health())


@router.get("/usage-overview")
def usage_overview(_: User = Depends(require_admin)):
    """返回用量总览骨架，后续可接入按日统计与排行数据。"""
    return ok({"days": 7, "today": {}, "trends": [], "llmRankings": [], "embeddingRankings": [], "alerts": []})


@router.get("/audit-logs")
def audit_logs(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return ok(list_audit_logs(db))


@router.get("/conversations")
def admin_conversations(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return ok(list_admin_conversations(db))


@router.get("/org-tags")
def org_tags(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return ok([serialize_org_tag(org) for org in db.scalars(select(OrgTag).order_by(OrgTag.tag_id)).all()])


@router.get("/org-tags/tree")
def org_tag_tree(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    """返回组织标签树，兼容前端组织管理树形控件的 children 字段。"""
    orgs = db.scalars(select(OrgTag).order_by(OrgTag.tag_id)).all()
    return ok(build_org_tree(orgs))


@router.post("/org-tags")
def create_org_tag(payload: OrgTagUpsertRequest, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    return ok(upsert_org_tag(db, payload.tagId, payload.name, payload.description, payload.parentTag, payload.uploadMaxSizeBytes))


@router.put("/org-tags/{tagId}")
def update_org_tag(tagId: str, payload: OrgTagUpsertRequest, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    return ok(upsert_org_tag(db, tagId, payload.name, payload.description, payload.parentTag, payload.uploadMaxSizeBytes))


@router.get("/rate-limits")
def rate_limits(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    """读取限流配置；缺失默认项会自动补齐，避免新部署后台页面空白。"""
    keys = ["chatMessage", "llmGlobalToken", "embeddingUploadToken", "embeddingQueryRequest", "embeddingQueryGlobalToken"]
    for key in keys:
        if not db.get(RateLimitConfig, key):
            db.add(RateLimitConfig(config_key=key))
    db.commit()
    rows = db.scalars(select(RateLimitConfig)).all()
    return ok({row.config_key: {"singleMax": row.single_max, "minuteMax": row.minute_max, "dayMax": row.day_max} for row in rows})


@router.put("/rate-limits/{configKey}")
def update_rate_limit(configKey: str, payload: RateLimitConfigRequest, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return ok(upsert_rate_limit(db, configKey, payload, current_user))


@router.get("/invite-codes")
def invite_codes(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return ok(list_invite_codes(db))


@router.post("/invite-codes")
def create_invite_code(payload: InviteCodeRequest, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return ok(upsert_invite_code(db, payload.code, payload.maxUses, payload.enabled, current_user))


@router.put("/invite-codes/{code}")
def update_invite_code(code: str, payload: InviteCodeRequest, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return ok(upsert_invite_code(db, code, payload.maxUses, payload.enabled, current_user))


@router.get("/model-providers")
def model_providers(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    """读取 LLM 与 Embedding 供应商配置，返回按 scope 分组的前端兼容结构。"""
    return ok(model_provider_settings(db))


@router.put("/model-providers")
def save_model_provider(payload: ModelProviderRequest, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return ok(upsert_model_provider(db, payload, current_user))


@router.put("/users/org-tags")
def assign_orgs(payload: UserOrgAssignRequest, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    assign_user_orgs(db, payload.userId, payload.orgTags, payload.primaryOrg)
    return ok(None)


@router.post("/minio/migrate")
def minio_migrate(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """将数据库内已有文档内容迁移到 MinIO，属于需要审计的运维操作。"""
    return ok(migrate_documents_to_minio(db, current_user))


@router.post("/system/cleanup-all")
def cleanup_all(payload: CleanupAllRequest, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """高危清理入口：必须同时满足管理员、环境开关和确认文本。"""
    return ok(cleanup_all_data(db, current_user, payload.confirmText))


@router.post("/users/token-grant")
def token_grant(payload: TokenGrantRequest, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    grant_tokens(db, payload.userId, payload.tokenType, payload.amount, payload.reason)
    return ok(None)


@router.get("/recharge/packages")
def admin_packages(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return ok(list_packages(db))


@router.post("/recharge/packages")
def admin_create_package(payload: RechargePackageRequest, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    return ok(
        create_package(
            db,
            package_name=payload.packageName,
            package_price=payload.packagePrice,
            package_desc=payload.packageDesc,
            package_benefit=payload.packageBenefit,
            llm_token=payload.llmToken,
            embedding_token=payload.embeddingToken,
            enabled=payload.enabled,
            sort_order=payload.sortOrder,
        )
    )
