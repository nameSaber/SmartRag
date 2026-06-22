def _login(client, username="chat-user"):
    client.post("/api/v1/users/register", json={"username": username, "password": "secret"})
    data = client.post("/api/v1/users/login", json={"username": username, "password": "secret"}).json()["data"]
    return data, {"Authorization": f"Bearer {data['token']}"}


def test_conversation_generation_feedback_and_websocket(client):
    login_data, headers = _login(client)

    session = client.post("/api/v1/users/conversations", headers=headers, json={"title": "测试会话"}).json()
    assert session["code"] == 200
    conversation_id = session["data"]["conversationId"]

    token_resp = client.get("/api/v1/chat/websocket-token", headers=headers).json()
    assert token_resp["code"] == 200

    with client.websocket_connect(f"/chat/{login_data['token']}") as websocket:
        assert websocket.receive_json()["type"] == "connected"
        websocket.send_json({"message": "你好 FastAPI", "conversationId": conversation_id})
        generated = websocket.receive_json()
        assert generated["type"] == "generation"
        generation_id = generated["data"]["generationId"]
        seen_delta = False
        while True:
            event = websocket.receive_json()
            if event["type"] == "delta":
                seen_delta = True
            if event["type"] == "done":
                break
        assert seen_delta is True
        websocket.send_json({"type": "cancel", "generationId": generation_id})
        assert websocket.receive_json()["type"] == "cancelled"

    snapshot = client.get(f"/api/v1/chat/generation/{generation_id}", headers=headers).json()
    assert snapshot["code"] == 200
    assert snapshot["data"]["status"] == "CANCELLED"

    history = client.get("/api/v1/users/conversation", headers=headers, params={"conversationId": conversation_id}).json()
    assert history["code"] == 200
    assert history["data"][0]["question"] == "你好 FastAPI"

    feedback = client.post("/api/v1/chat/feedback", headers=headers, json={"rating": "UP", "generationId": generation_id}).json()
    assert feedback["code"] == 200

    archived = client.put(f"/api/v1/users/conversations/{conversation_id}/archive", headers=headers).json()
    assert archived["code"] == 200
    assert archived["data"]["status"] == "ARCHIVED"
