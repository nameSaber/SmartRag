def test_llm_gateway_streams_text_chunks():
    from app.integrations.llm import LlmGateway

    chunks = list(LlmGateway().stream_text("hello streaming world"))

    assert chunks == ["hello ", "streaming ", "world "]

