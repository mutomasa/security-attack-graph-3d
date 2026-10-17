import json

import httpx
import pytest

from backend.config import LLMSettings
from backend.models.schemas import AttackPath
from backend.services.guided_schemas import explanation_schema, intent_schema
from backend.services.intent_service import FallbackIntentParser, LLMIntentParser, RuleBasedIntentParser
from backend.services.llm_service import LLMError, OpenAICompatibleClient
from backend.services.seed_loader import load_all_scenarios
from backend.services.summary_service import (
    GuidedLLMSummarizer,
    SafeSummarizer,
    render_guided_explanation,
    validate_guided_explanation,
)

A = load_all_scenarios()["demo_company_a"]
PATH = AttackPath(
    score=10,
    nodes=[{"id": "i", "label": "Internet", "type": "NetworkZone"},
           {"id": "w", "label": "Web Server", "type": "Asset"},
           {"id": "d", "label": "Customer Data", "type": "Data"}],
    edges=[{"source": "i", "target": "w", "type": "EXPOSED_TO"}, {"source": "w", "target": "d", "type": "STORES"}],
)
GOOD = {
    "steps": [{"node": "Internet", "event": "外部から到達"}, {"node": "Web Server", "event": "侵害される"},
              {"node": "Customer Data", "event": "持ち出される"}],
    "root_cause": "公開サーバに顧客データがある",
    "priority_fix": "Web Server",
}


class FakeLLM:
    def __init__(self, reply):
        self.reply = reply
        self.kwargs = {}

    def complete(self, prompt, **kwargs):
        self.kwargs = kwargs
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply if isinstance(self.reply, str) else json.dumps(self.reply, ensure_ascii=False)


def test_intent_schema_restricts_endpoints_to_scenario_labels():
    schema = intent_schema(A)
    assert set(schema["properties"]["intent"]["enum"]) == {
        "find_highest_risk_path", "list_attack_paths", "blast_radius", "required_permissions"}
    endpoints = schema["properties"]["source"]["enum"]
    assert "CVE-XXXX" in endpoints and None in endpoints and "Mainframe" not in endpoints


def test_explanation_schema_pins_each_step_to_path_order():
    schema = explanation_schema(PATH)
    steps = schema["properties"]["steps"]
    assert [s["properties"]["node"]["const"] for s in steps["prefixItems"]] == ["Internet", "Web Server",
                                                                               "Customer Data"]
    assert steps["items"] is False and steps["minItems"] == 3
    assert schema["properties"]["priority_fix"]["enum"] == ["Customer Data", "Internet", "Web Server"]


def test_client_sends_json_schema_response_format():
    seen = {}

    def handler(request):
        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    client = OpenAICompatibleClient(LLMSettings(True, "http://llm/v1", "m", 1), transport=httpx.MockTransport(handler))
    client.complete("q", json_mode=True, json_schema={"type": "object"})
    assert seen["response_format"]["type"] == "json_schema"
    assert seen["response_format"]["json_schema"]["schema"] == {"type": "object"}


def test_guided_intent_parser_passes_schema():
    llm = FakeLLM({"intent": "blast_radius", "source": "Service Account", "target": None})
    result = FallbackIntentParser(LLMIntentParser(llm, guided=True), RuleBasedIntentParser()).parse("SAは？", A)
    assert llm.kwargs["json_schema"] == intent_schema(A)
    assert (result.intent.value, result.source, result.parsed_by) == ("blast_radius", "Service Account", "llm")


def test_guided_summarizer_renders_steps_with_exact_node_names():
    llm = FakeLLM(GOOD)
    text = GuidedLLMSummarizer(llm).summarize("q", PATH)
    assert llm.kwargs["json_schema"] == explanation_schema(PATH)
    assert text.splitlines()[0] == "1. **Internet** — 外部から到達"
    assert "根本原因: 公開サーバに顧客データがある" in text
    assert text.endswith("最優先で塞ぐべき箇所: **Web Server**")


@pytest.mark.parametrize(
    "broken",
    [
        {**GOOD, "steps": GOOD["steps"][::-1]},
        {**GOOD, "steps": [{**GOOD["steps"][0], "node": "インターネット"}, *GOOD["steps"][1:]]},
        {**GOOD, "priority_fix": "ウェブサーバー"},
        {**GOOD, "steps": [*GOOD["steps"][:2], {"node": "Customer Data", "event": "  "}]},
        {**GOOD, "steps": ["Internet", "Web Server", "Customer Data"]},
    ],
)
def test_invalid_guided_output_is_rejected(broken):
    with pytest.raises(LLMError):
        validate_guided_explanation(broken, PATH)
    assert SafeSummarizer(GuidedLLMSummarizer(FakeLLM(broken))).summarize("q", PATH) is None


def test_render_without_root_cause():
    text = render_guided_explanation({**GOOD, "root_cause": ""})
    assert "根本原因" not in text
