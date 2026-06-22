import httpx

from app.core.config import settings


class LlmGateway:
    def generate(self, question: str, references: list[dict]) -> str:
        if settings.llm_backend == "openai_compatible":
            return self._generate_openai_compatible(question, references)
        return self._generate_mock(question, references)

    def _generate_mock(self, question: str, references: list[dict]) -> str:
        # mock 后端用于本地测试和无外部模型时的联调，保留引用语义。
        if references:
            return f"根据知识库检索结果：{references[0]['matchedChunkText']}"
        return f"已收到问题：{question}"

    def _generate_openai_compatible(self, question: str, references: list[dict]) -> str:
        if not settings.llm_api_base_url or not settings.llm_api_key:
            raise RuntimeError("LLM 配置不完整")
        reference_text = "\n".join(item.get("matchedChunkText", "") for item in references[:5])
        payload = {
            "model": settings.llm_model_name,
            "messages": [
                {"role": "system", "content": "请先给出结论，再给出依据。若信息不足，请明确说明。"},
                {"role": "user", "content": f"参考资料：\n{reference_text}\n\n问题：{question}"},
            ],
        }
        headers = {"Authorization": f"Bearer {settings.llm_api_key}"}
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            response = client.post(settings.llm_api_base_url.rstrip("/") + "/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"]["content"]


def estimate_tokens(*texts: str) -> int:
    # 粗略估算用于额度控制；真实供应商返回 usage 后可替换为精确值。
    char_count = sum(len(text or "") for text in texts)
    return max(1, char_count // 2)


def get_llm_gateway() -> LlmGateway:
    return LlmGateway()
