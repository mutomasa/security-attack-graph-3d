import json

import httpx
import pytest

from backend.config import LLMSettings
from backend.services.llm_service import LLMError, OpenAICompatibleClient, extract_json_object, render_prompt

SETTINGS = LLMSettings(enabled=True, base_url="http://llm/v1", model="qwen", timeout=1)


def _client(handler) -> OpenAICompatibleClient:
    return OpenAICompatibleClient(SETTINGS, transport=httpx.MockTransport(handler))


def test_complete_posts_chat_request_and_returns_content():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "hi"}}]})

    assert _client(handler).complete("q", json_mode=True) == "hi"
    assert seen["path"] == "/v1/chat/completions"
    assert seen["body"]["model"] == "qwen"
    assert seen["body"]["response_format"] == {"type": "json_object"}
    assert seen["body"]["temperature"] == 0.0


def test_http_error_becomes_llm_error():
    with pytest.raises(LLMError):
        _client(lambda r: httpx.Response(500)).complete("q")


def test_malformed_response_becomes_llm_error():
    with pytest.raises(LLMError):
        _client(lambda r: httpx.Response(200, json={"oops": 1})).complete("q")


def test_connection_error_becomes_llm_error():
    def handler(request):
        raise httpx.ConnectError("refused")

    with pytest.raises(LLMError):
        _client(handler).complete("q")


def test_extract_json_from_fenced_output():
    assert extract_json_object('```json\n{"intent": "x"}\n```') == {"intent": "x"}


def test_extract_json_rejects_garbage():
    with pytest.raises(LLMError):
        extract_json_object("no json here")


def test_render_prompt_keeps_json_braces():
    assert render_prompt('{"a": 1} {name}', name="X") == '{"a": 1} X'
