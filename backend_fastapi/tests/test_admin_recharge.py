def _login(client, username, password="secret"):
    client.post("/api/v1/users/register", json={"username": username, "password": password})
    data = client.post("/api/v1/users/login", json={"username": username, "password": password}).json()["data"]
    return data, {"Authorization": f"Bearer {data['token']}"}


def _make_admin(username):
    from sqlalchemy import select

    from app.core.database import SessionLocal
    from app.models.user import User

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.username == username))
        user.role = "ADMIN"
        db.commit()
    finally:
        db.close()


def test_admin_org_token_grant_and_recharge_callback(client):
    _, user_headers = _login(client, "pay-user")
    _, admin_headers = _login(client, "root-admin")
    _make_admin("root-admin")

    status = client.get("/api/v1/admin/status", headers=admin_headers).json()
    assert status["code"] == 200
    assert status["data"]["status"] in {"UP", "DEGRADED"}
    assert "dependencies" in status["data"]

    users = client.get("/api/v1/admin/users", headers=admin_headers).json()
    assert users["code"] == 200
    pay_user = next(item for item in users["data"] if item["username"] == "pay-user")

    org = client.post("/api/v1/admin/org-tags", headers=admin_headers, json={"tagId": "sales", "name": "销售部"}).json()
    assert org["code"] == 200
    assert org["data"]["tagId"] == "sales"

    grant = client.post("/api/v1/admin/users/token-grant", headers=admin_headers, json={"userId": pay_user["id"], "tokenType": "LLM", "amount": 123, "reason": "测试增发"}).json()
    assert grant["code"] == 200

    packages = client.get("/api/v1/recharge/packages").json()
    assert packages["code"] == 200
    package_id = packages["data"][0]["id"]

    order = client.post("/api/v1/recharge/create-order", headers=user_headers, json={"packageId": package_id}).json()
    assert order["code"] == 200
    trade_no = order["data"]["tradeNo"]

    callback = client.post("/api/v1/recharge/pay-callback", json={"tradeNo": trade_no, "transactionId": "wx-001", "status": "SUCCEED"}).json()
    assert callback["code"] == 200
    assert callback["data"]["status"] == "SUCCEED"

    records = client.get("/api/v1/users/token-records", headers=user_headers).json()
    assert records["code"] == 200
    assert records["data"]["totalElements"] >= 4
