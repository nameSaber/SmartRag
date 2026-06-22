def test_register_login_refresh_and_me(client):
    resp = client.post("/api/v1/users/register", json={"username": "alice", "password": "secret"})
    assert resp.json()["code"] == 200

    login = client.post("/api/v1/users/login", json={"username": "alice", "password": "secret"}).json()
    assert login["code"] == 200
    token = login["data"]["token"]
    refresh_token = login["data"]["refreshToken"]

    me = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["code"] == 200
    assert me["data"]["username"] == "alice"
    assert me["data"]["role"] == "USER"
    assert me["data"]["primaryOrg"] == "default"

    refreshed = client.post("/api/v1/auth/refreshToken", json={"refreshToken": refresh_token}).json()
    assert refreshed["code"] == 200
    assert refreshed["data"]["token"]


def test_duplicate_register_and_bad_login_fail(client):
    assert client.post("/api/v1/users/register", json={"username": "bob", "password": "secret"}).json()["code"] == 200
    duplicate = client.post("/api/v1/users/register", json={"username": "bob", "password": "secret"}).json()
    assert duplicate["code"] == 400
    assert "用户名已存在" in duplicate["message"]

    bad_login = client.post("/api/v1/users/login", json={"username": "bob", "password": "wrong"}).json()
    assert bad_login["code"] == 401


def test_org_usage_logout_all_and_token_records(client):
    client.post("/api/v1/users/register", json={"username": "cindy", "password": "secret"})
    token = client.post("/api/v1/users/login", json={"username": "cindy", "password": "secret"}).json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    orgs = client.get("/api/v1/users/org-tags", headers=headers).json()
    assert orgs["code"] == 200
    assert orgs["data"]["orgTags"] == ["default"]

    usage = client.get("/api/v1/users/usage", headers=headers).json()
    assert usage["code"] == 200
    assert usage["data"]["llm"]["remainingTokens"] > 0

    records = client.get("/api/v1/users/token-records", headers=headers).json()
    assert records["code"] == 200
    assert records["data"]["totalElements"] == 2

    assert client.post("/api/v1/users/logout-all", headers=headers).json()["code"] == 200
    expired = client.get("/api/v1/users/me", headers=headers).json()
    assert expired["code"] == 401

