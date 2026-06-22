def _login(client, username="uploader"):
    client.post("/api/v1/users/register", json={"username": username, "password": "secret"})
    token = client.post("/api/v1/users/login", json={"username": username, "password": "secret"}).json()["data"]["token"]
    return {"Authorization": f"Bearer {token}"}


def test_upload_merge_preview_download_and_search(client):
    headers = _login(client)
    file_md5 = "md5-upload-001"
    text = "PaiSmart 支持 FastAPI 文档上传和企业知识库检索"

    chunk_resp = client.post(
        "/api/v1/upload/chunk",
        headers=headers,
        data={"fileMd5": file_md5, "chunkIndex": 0, "totalChunks": 1, "fileName": "demo.txt", "totalSize": len(text)},
        files={"file": ("demo.txt", text.encode("utf-8"), "text/plain")},
    ).json()
    assert chunk_resp["code"] == 200
    assert chunk_resp["data"]["uploadedChunks"] == [0]

    status = client.get("/api/v1/upload/status", headers=headers, params={"fileMd5": file_md5}).json()
    assert status["code"] == 200
    assert status["data"]["progress"] == 100

    merged = client.post(
        "/api/v1/upload/merge",
        headers=headers,
        json={"fileMd5": file_md5, "fileName": "demo.txt", "totalChunks": 1, "totalSize": len(text), "isPublic": False},
    ).json()
    assert merged["code"] == 200
    assert merged["data"]["vectorizationStatus"] == "COMPLETED"

    docs = client.get("/api/v1/documents/accessible", headers=headers).json()
    assert docs["code"] == 200
    assert docs["data"][0]["fileMd5"] == file_md5

    preview = client.get("/api/v1/documents/preview", headers=headers, params={"fileMd5": file_md5}).json()
    assert preview["code"] == 200
    assert "企业知识库" in preview["data"]["content"]

    download = client.get("/api/v1/documents/download-by-md5", headers=headers, params={"fileMd5": file_md5})
    assert download.status_code == 200
    assert "FastAPI" in download.text

    search = client.get("/api/v1/search/hybrid", headers=headers, params={"query": "企业知识库", "topK": 5}).json()
    assert search["code"] == 200
    assert search["data"][0]["fileMd5"] == file_md5
    assert search["data"][0]["retrievalMode"] == "keyword"

