def test_elasticsearch_search_consumes_embedding_tokens(client, monkeypatch):
    from app.core import config as config_module
    from app.services import document_service

    class FakeSearchIndex:
        def search(self, query, user_id, org_tags, top_k, query_vector=None):
            return [
                {
                    "fileMd5": "x",
                    "chunkId": 0,
                    "textContent": query,
                    "score": 1.0,
                    "retrievalMode": "hybrid",
                    "matchedChunkText": query,
                }
            ]

    config_module.settings.search_backend = "elasticsearch"
    monkeypatch.setattr(document_service, "get_search_index", lambda: FakeSearchIndex())
    headers = _login(client, "hybrid-user")

    result = client.get("/api/v1/search/hybrid", headers=headers, params={"query": "混合检索", "topK": 3}).json()
    records = client.get("/api/v1/users/token-records", headers=headers).json()["data"]["content"]

    assert result["code"] == 200
    assert result["data"][0]["retrievalMode"] == "hybrid"
    assert any(item["tokenType"] == "EMBEDDING" and item["reason"] == "检索向量化" for item in records)
    config_module.settings.search_backend = "database"


def _login(client, username):
    client.post("/api/v1/users/register", json={"username": username, "password": "secret"})
    token = client.post("/api/v1/users/login", json={"username": username, "password": "secret"}).json()["data"]["token"]
    return {"Authorization": f"Bearer {token}"}

