def test_parse_openai_sse_line_extracts_deepseek_delta():
    from app.integrations.llm import parse_openai_sse_line

    line = 'data: {"choices":[{"delta":{"content":"你好"},"finish_reason":null}]}'

    assert parse_openai_sse_line(line) == "你好"
    assert parse_openai_sse_line("data: [DONE]") is None


def test_deepseek_defaults_are_configured():
    from app.core.config import settings

    assert settings.llm_api_base_url == "https://api.deepseek.com"
    assert settings.llm_model_name == "deepseek-v4-flash"

