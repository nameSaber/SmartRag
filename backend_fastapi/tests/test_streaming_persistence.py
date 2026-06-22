def test_streaming_generation_persists_incremental_content(client):
    from app.core.database import SessionLocal
    from app.models.chat import Generation

    login_data, headers = _login(client, "stream-persist-user")
    with client.websocket_connect(f"/chat/{login_data['token']}") as websocket:
        websocket.receive_json()
        websocket.send_json({"message": "persist chunks"})
        generation = websocket.receive_json()
        generation_id = generation["data"]["generationId"]
        first_delta = websocket.receive_json()
        assert first_delta["type"] == "delta"

        db = SessionLocal()
        try:
            row = db.get(Generation, generation_id)
            assert row.content.startswith(first_delta["content"])
        finally:
            db.close()

        while websocket.receive_json()["type"] != "done":
            pass

    snapshot = client.get(f"/api/v1/chat/generation/{generation_id}", headers=headers).json()
    assert snapshot["data"]["status"] == "COMPLETED"
    assert snapshot["data"]["content"].startswith(first_delta["content"])


def _login(client, username):
    client.post("/api/v1/users/register", json={"username": username, "password": "secret"})
    data = client.post("/api/v1/users/login", json={"username": username, "password": "secret"}).json()["data"]
    return data, {"Authorization": f"Bearer {data['token']}"}
