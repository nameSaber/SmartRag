from sqlalchemy import select


def test_admin_conversations_audit_and_cleanup_guard(client, monkeypatch):
    admin_headers = _login(client, "ops-admin")
    user_headers = _login(client, "ops-user")
    _make_admin("ops-admin")

    client.post("/api/v1/users/conversations", headers=user_headers, json={"title": "运维可见会话"})
    conversations = client.get("/api/v1/admin/conversations", headers=admin_headers).json()
    assert conversations["code"] == 200
    assert len(conversations["data"]) == 1

    blocked = client.post("/api/v1/admin/system/cleanup-all", headers=admin_headers, json={"confirmText": "CONFIRM_CLEANUP_ALL"}).json()
    assert blocked["code"] == 403

    logs = client.get("/api/v1/admin/audit-logs", headers=admin_headers).json()
    assert logs["code"] == 200


def test_minio_migration_writes_audit_log(client, monkeypatch):
    from app.services import admin_service

    class FakeStorage:
        def __init__(self):
            self.objects = []

        def put_bytes(self, key, content, content_type):
            self.objects.append((key, content, content_type))

    fake = FakeStorage()
    monkeypatch.setattr(admin_service, "get_object_storage", lambda: fake)

    admin_headers = _login(client, "migrate-admin")
    _make_admin("migrate-admin")
    _upload_doc(client, admin_headers)

    result = client.post("/api/v1/admin/minio/migrate", headers=admin_headers).json()
    assert result["code"] == 200
    assert result["data"]["migrated"] == 1
    assert len(fake.objects) == 1

    logs = client.get("/api/v1/admin/audit-logs", headers=admin_headers).json()
    assert any(item["action"] == "MINIO_MIGRATE" for item in logs["data"])


def _upload_doc(client, headers):
    text = "migration document"
    client.post(
        "/api/v1/upload/chunk",
        headers=headers,
        data={"fileMd5": "migrate-md5", "chunkIndex": 0, "totalChunks": 1, "fileName": "migrate.txt", "totalSize": len(text)},
        files={"file": ("migrate.txt", text.encode("utf-8"), "text/plain")},
    )
    client.post("/api/v1/upload/merge", headers=headers, json={"fileMd5": "migrate-md5", "fileName": "migrate.txt", "totalChunks": 1})


def _login(client, username):
    client.post("/api/v1/users/register", json={"username": username, "password": "secret"})
    token = client.post("/api/v1/users/login", json={"username": username, "password": "secret"}).json()["data"]["token"]
    return {"Authorization": f"Bearer {token}"}


def _make_admin(username):
    from app.core.database import SessionLocal
    from app.models.user import User

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.username == username))
        user.role = "ADMIN"
        db.commit()
    finally:
        db.close()

