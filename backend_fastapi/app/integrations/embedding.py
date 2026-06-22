import hashlib

import httpx

from app.core.config import settings


class EmbeddingGateway:
    """Embedding 统一网关，支持真实 OpenAI-compatible 服务和稳定 mock 向量。"""

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if settings.embedding_backend == "openai_compatible":
            return self._embed_openai_compatible(texts)
        return [self._mock_vector(text) for text in texts]

    def _mock_vector(self, text: str) -> list[float]:
        # mock 向量保证同样文本得到稳定结果，便于本地测试和离线开发。
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [round(digest[index] / 255, 6) for index in range(settings.embedding_dimension)]

    def _embed_openai_compatible(self, texts: list[str]) -> list[list[float]]:
        if not settings.embedding_api_base_url or not settings.embedding_api_key:
            raise RuntimeError("Embedding 配置不完整")
        payload = {"model": settings.embedding_model_name, "input": texts}
        headers = {"Authorization": f"Bearer {settings.embedding_api_key}"}
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            response = client.post(settings.embedding_api_base_url.rstrip("/") + "/embeddings", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        vectors = [item["embedding"] for item in data["data"]]
        for vector in vectors:
            if len(vector) != settings.embedding_dimension:
                raise RuntimeError("Embedding 维度与配置不一致")
        return vectors


def estimate_embedding_tokens(texts: list[str]) -> int:
    """粗略估算 embedding token，用于上传向量化和检索向量化的额度扣减。"""
    return max(1, sum(len(text or "") for text in texts) // 2)


def get_embedding_gateway() -> EmbeddingGateway:
    return EmbeddingGateway()
