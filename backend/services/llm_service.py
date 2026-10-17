"""LLM access through an OpenAI-compatible chat API (vLLM serving Qwen)."""

import json
import re
from pathlib import Path
from typing import Protocol

import httpx

from backend.config import LLMSettings

PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"


class LLMError(RuntimeError):
    pass


class LLMClient(Protocol):
    def complete(self, prompt: str, *, json_mode: bool = False, max_tokens: int = 256) -> str: ...


class OpenAICompatibleClient:
    def __init__(self, settings: LLMSettings, transport: httpx.BaseTransport | None = None) -> None:
        self._model = settings.model
        self._disable_thinking = settings.disable_thinking
        self._http = httpx.Client(base_url=settings.base_url, timeout=settings.timeout, transport=transport)

    def complete(self, prompt: str, *, json_mode: bool = False, max_tokens: int = 256) -> str:
        try:
            response = self._http.post("/chat/completions", json=self._payload(prompt, json_mode, max_tokens))
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise LLMError(f"LLM request failed: {exc}") from exc

    def _payload(self, prompt: str, json_mode: bool, max_tokens: int) -> dict:
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        if self._disable_thinking:
            payload["chat_template_kwargs"] = {"enable_thinking": False}
        return payload


def load_prompt(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8")


def render_prompt(template: str, **values: str) -> str:
    """Replace `{key}` placeholders without touching other braces (prompts contain JSON examples)."""
    for key, value in values.items():
        template = template.replace("{" + key + "}", str(value))
    return template


def extract_json_object(text: str) -> dict:
    """Small models sometimes wrap JSON in prose or code fences; take the first {...} block."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise LLMError(f"no JSON object in LLM output: {text[:200]!r}")
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise LLMError(f"invalid JSON from LLM: {exc}") from exc
