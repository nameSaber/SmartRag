def test_pay_callback_signature_is_verified(client, monkeypatch):
    from app.core import config as config_module
    from app.integrations.wechat_pay import build_callback_signature

    config_module.settings.wx_pay_callback_secret = "secret"

    client.post("/api/v1/users/register", json={"username": "wx-user", "password": "secret"})
    token = client.post("/api/v1/users/login", json={"username": "wx-user", "password": "secret"}).json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    package_id = client.get("/api/v1/recharge/packages").json()["data"][0]["id"]
    trade_no = client.post("/api/v1/recharge/create-order", headers=headers, json={"packageId": package_id}).json()["data"]["tradeNo"]

    bad = client.post("/api/v1/recharge/pay-callback", json={"tradeNo": trade_no, "transactionId": "wx-bad", "status": "SUCCEED", "signature": "bad"}).json()
    assert bad["code"] == 401

    signature = build_callback_signature(trade_no, "wx-good", "SUCCEED", "secret")
    ok = client.post("/api/v1/recharge/pay-callback", json={"tradeNo": trade_no, "transactionId": "wx-good", "status": "SUCCEED", "signature": signature}).json()
    assert ok["code"] == 200
    assert ok["data"]["status"] == "SUCCEED"

    config_module.settings.wx_pay_callback_secret = ""

