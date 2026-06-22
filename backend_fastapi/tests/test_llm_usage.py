def test_chat_generation_consumes_llm_tokens(client):
    client.post("/api/v1/users/register", json={"username": "llm-user", "password": "secret"})
    token = client.post("/api/v1/users/login", json={"username": "llm-user", "password": "secret"}).json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    before = client.get("/api/v1/users/usage", headers=headers).json()["data"]["llm"]["remainingTokens"]
    session = client.post("/api/v1/users/conversations", headers=headers, json={"title": "额度测试"}).json()["data"]
    with client.websocket_connect(f"/chat/{token}") as websocket:
        websocket.receive_json()
        websocket.send_json({"message": "测试 token 消费", "conversationId": session["conversationId"]})
        websocket.receive_json()
        websocket.receive_json()

    after = client.get("/api/v1/users/usage", headers=headers).json()["data"]["llm"]["remainingTokens"]
    records = client.get("/api/v1/users/token-records", headers=headers).json()["data"]["content"]

    assert after < before
    assert any(item["changeType"] == "CONSUME" and item["tokenType"] == "LLM" for item in records)

