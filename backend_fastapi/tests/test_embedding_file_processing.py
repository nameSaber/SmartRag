def test_embedding_gateway_returns_configured_dimension(monkeypatch):
    from app.core import config as config_module
    from app.integrations.embedding import get_embedding_gateway

    config_module.settings.embedding_dimension = 8
    vector = get_embedding_gateway().embed_texts(["hello"])[0]

    assert len(vector) == 8
    assert all(0 <= item <= 1 for item in vector)


def test_upload_merge_creates_embedding_records(client):
    headers = _login(client, "embedding-user")
    file_md5 = "embed-md5-001"
    text = "用于测试 embedding token 消耗和切块向量写入"

    client.post(
        "/api/v1/upload/chunk",
        headers=headers,
        data={"fileMd5": file_md5, "chunkIndex": 0, "totalChunks": 1, "fileName": "embed.txt", "totalSize": len(text)},
        files={"file": ("embed.txt", text.encode("utf-8"), "text/plain")},
    )
    merged = client.post(
        "/api/v1/upload/merge",
        headers=headers,
        json={"fileMd5": file_md5, "fileName": "embed.txt", "totalChunks": 1, "totalSize": len(text)},
    ).json()

    assert merged["code"] == 200
    records = client.get("/api/v1/users/token-records", headers=headers).json()["data"]["content"]
    assert any(item["tokenType"] == "EMBEDDING" and item["changeType"] == "CONSUME" for item in records)


def test_file_processing_task_rebuilds_document_index(client):
    from app.core.database import SessionLocal
    from app.tasks.file_processing import process_file_task

    headers = _login(client, "task-user")
    file_md5 = "task-md5-001"
    text = "Kafka consumer rebuild index text"
    client.post(
        "/api/v1/upload/chunk",
        headers=headers,
        data={"fileMd5": file_md5, "chunkIndex": 0, "totalChunks": 1, "fileName": "task.txt", "totalSize": len(text)},
        files={"file": ("task.txt", text.encode("utf-8"), "text/plain")},
    )
    client.post("/api/v1/upload/merge", headers=headers, json={"fileMd5": file_md5, "fileName": "task.txt", "totalChunks": 1})

    db = SessionLocal()
    try:
        result = process_file_task(db, {"fileMd5": file_md5})
    finally:
        db.close()

    assert result["fileMd5"] == file_md5
    assert result["chunkCount"] >= 1
    assert result["vectorizationStatus"] == "COMPLETED"


def _login(client, username):
    client.post("/api/v1/users/register", json={"username": username, "password": "secret"})
    token = client.post("/api/v1/users/login", json={"username": username, "password": "secret"}).json()["data"]["token"]
    return {"Authorization": f"Bearer {token}"}

