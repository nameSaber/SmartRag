import json
from collections.abc import Iterable

import httpx

from app.core.config import settings


class LlmGateway:
    """LLM 统一网关。

    对业务层隐藏 DeepSeek/OpenAI-compatible 与 mock 后端差异，保证聊天服务只依赖 generate/stream 两种能力。
    """

    def generate(self, question: str, references: list[dict]) -> str:
        if settings.llm_backend == "openai_compatible":
            return self._generate_openai_compatible(question, references)
        return self._generate_mock(question, references)

    def stream(self, question: str, references: list[dict]) -> Iterable[str]:
        if settings.llm_backend == "openai_compatible":
            yield from self._stream_openai_compatible(question, references)
            return
        yield from self.stream_text(self._generate_mock(question, references))

    def stream_text(self, content: str) -> Iterable[str]:
        # 本地 mock 流式输出按词切片，真实 DeepSeek/OpenAI-compatible 流式输出走 SSE。
        parts = content.split()
        if not parts:
            yield content
            return
        for part in parts:
            yield part + " "

    def _generate_mock(self, question: str, references: list[dict]) -> str:
        # mock 后端用于本地测试和无外部模型时的联调，保留引用语义。
        if references:
            return f"根据知识库检索结果：{references[0]['matchedChunkText']}"
        return f"已收到问题：{question}"

    def _build_payload(self, question: str, references: list[dict], stream: bool) -> dict:
        """构造 RAG 问答请求体，把检索引用压入 user prompt 并保留统一系统提示词。"""
        reference_text = "\n".join(item.get("matchedChunkText", "") for item in references[:5])
        return {
            "model": settings.llm_model_name,
            "messages": [
                {"role": "system", "content": "请先给出结论，再给出依据。若信息不足，请明确说明。"},
                {"role": "user", "content": f"参考资料：\n{reference_text}\n\n问题：{question}"},
            ],
            "stream": stream,
            # DeepSeek V4 默认开启 thinking；这里显式关闭，保持 RAG 问答响应更直接。
            "thinking": {"type": "disabled"},
        }

    def _headers(self) -> dict:
        if not settings.llm_api_base_url or not settings.llm_api_key:
            raise RuntimeError("LLM 配置不完整")
        return {"Authorization": f"Bearer {settings.llm_api_key}", "Content-Type": "application/json"}

    def _generate_openai_compatible(self, question: str, references: list[dict]) -> str:
        payload = self._build_payload(question, references, stream=False)
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            response = client.post(settings.llm_api_base_url.rstrip("/") + "/chat/completions", json=payload, headers=self._headers())
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"]["content"]

    def _stream_openai_compatible(self, question: str, references: list[dict]) -> Iterable[str]:
        payload = self._build_payload(question, references, stream=True)
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            with client.stream("POST", settings.llm_api_base_url.rstrip("/") + "/chat/completions", json=payload, headers=self._headers()) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    chunk = parse_openai_sse_line(line)
                    if chunk:
                        yield chunk


def parse_openai_sse_line(line: str) -> str | None:
    """解析 OpenAI-compatible SSE 单行数据，只返回本次 delta 中新增的正文片段。"""
    if not line or not line.startswith("data:"):
        return None
    data = line.removeprefix("data:").strip()
    if data == "[DONE]":
        return None
    payload = json.loads(data)
    delta = payload.get("choices", [{}])[0].get("delta", {})
    return delta.get("content") or None


def estimate_tokens(*texts: str) -> int:
    # 粗略估算用于额度控制；真实供应商返回 usage 后可替换为精确值。
    char_count = sum(len(text or "") for text in texts)
    return max(1, char_count // 2)


def get_llm_gateway() -> LlmGateway:
    return LlmGateway()
