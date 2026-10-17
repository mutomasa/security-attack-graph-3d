"""Runtime settings read from environment variables."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Neo4jSettings:
    uri: str
    user: str
    password: str


def neo4j_settings() -> Neo4jSettings:
    return Neo4jSettings(
        uri=os.environ.get("NEO4J_URI", "bolt://localhost:17687"),
        user=os.environ.get("NEO4J_USER", "neo4j"),
        password=os.environ.get("NEO4J_PASSWORD", "attackgraph"),
    )


def graph_backend() -> str:
    """'neo4j' or 'memory'."""
    return os.environ.get("GRAPH_BACKEND", "neo4j")


@dataclass(frozen=True)
class LLMSettings:
    enabled: bool
    base_url: str
    model: str
    timeout: float
    disable_thinking: bool = True
    guided: bool = True


def llm_settings() -> LLMSettings:
    return LLMSettings(
        enabled=os.environ.get("LLM_ENABLED", "1") == "1",
        # 8000 is often taken locally; scripts/run_vllm.sh serves on 8001.
        base_url=os.environ.get("VLLM_BASE_URL", "http://localhost:8001/v1"),
        model=os.environ.get("VLLM_MODEL", "Qwen/Qwen3-1.7B"),
        timeout=float(os.environ.get("LLM_TIMEOUT", "20")),
        # Qwen3 emits <think> blocks by default; vLLM forwards this flag to the chat template.
        disable_thinking=os.environ.get("LLM_DISABLE_THINKING", "1") == "1",
        # Constrain LLM output with JSON Schema (node names as enums). Needs vLLM structured outputs.
        guided=os.environ.get("LLM_GUIDED", "1") == "1",
    )
