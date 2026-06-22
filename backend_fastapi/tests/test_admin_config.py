from sqlalchemy import select


def _login(client, username):
    client.post("/api/v1/users/register", json={"username": username, "password": "secret"})
    data = client.post("/api/v1/users/login", json={"username": username, "password": "secret"}).json()["data"]
    return {"Authorization": f"Bearer {data['token']}"}


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


def test_admin_invite_rate_model_and_user_org_assignment(client):
    admin_headers = _login(client, "config-admin")
    user_headers = _login(client, "normal-user")
    _make_admin("config-admin")

    created_org = client.post("/api/v1/admin/org-tags", headers=admin_headers, json={"tagId": "rd", "name": "研发部"}).json()
    assert created_org["code"] == 200

    users = client.get("/api/v1/admin/users", headers=admin_headers).json()["data"]
    normal_user = next(item for item in users if item["username"] == "normal-user")
    assign = client.put("/api/v1/admin/users/org-tags", headers=admin_headers, json={"userId": normal_user["id"], "orgTags": ["rd"], "primaryOrg": "rd"}).json()
    assert assign["code"] == 200
    me = client.get("/api/v1/users/me", headers=user_headers).json()
    assert me["data"]["primaryOrg"] == "rd"

    invite = client.post("/api/v1/admin/invite-codes", headers=admin_headers, json={"code": "INV-1", "maxUses": 2}).json()
    assert invite["code"] == 200
    assert invite["data"]["code"] == "INV-1"

    rate = client.put("/api/v1/admin/rate-limits/chatMessage", headers=admin_headers, json={"singleMax": 5, "singleWindowSeconds": 60, "minuteMax": 10, "minuteWindowSeconds": 60, "dayMax": 100, "dayWindowSeconds": 86400}).json()
    assert rate["code"] == 200
    assert rate["data"]["singleMax"] == 5

    provider = client.put("/api/v1/admin/model-providers", headers=admin_headers, json={"scope": "llm", "provider": "mock", "displayName": "Mock", "active": True}).json()
    assert provider["code"] == 200
    settings = client.get("/api/v1/admin/model-providers", headers=admin_headers).json()
    assert settings["data"]["llm"]["activeProvider"] == "mock"


def test_admin_org_tag_tree(client):
    admin_headers = _login(client, "tree-admin")
    _make_admin("tree-admin")

    client.post("/api/v1/admin/org-tags", headers=admin_headers, json={"tagId": "company", "name": "公司"})
    client.post(
        "/api/v1/admin/org-tags",
        headers=admin_headers,
        json={"tagId": "rd-child", "name": "研发组", "parentTag": "company"},
    )

    result = client.get("/api/v1/admin/org-tags/tree", headers=admin_headers).json()

    assert result["code"] == 200
    company = next(item for item in result["data"] if item["tagId"] == "company")
    assert company["children"][0]["tagId"] == "rd-child"
    assert company["children"][0]["children"] == []
