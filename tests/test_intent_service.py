import pytest

from backend.models.ontology import ATTACK_EDGE_TYPES, EdgeType
from backend.models.schemas import Intent, IntentType
from backend.services.intent_service import (
    FallbackIntentParser,
    LLMIntentParser,
    RuleBasedIntentParser,
    apply_guardrails,
    classify_intent,
)
from backend.services.llm_service import LLMError
from backend.services.seed_loader import load_all_scenarios

SCENARIOS = load_all_scenarios()
A = SCENARIOS["demo_company_a"]


class FakeLLM:
    def __init__(self, reply: str | Exception):
        self.reply = reply
        self.prompts: list[str] = []

    def complete(self, prompt, *, json_mode=False, max_tokens=256):
        self.prompts.append(prompt)
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


def _parse(question, scenario=A, llm=None):
    primary = LLMIntentParser(llm) if llm else None
    return FallbackIntentParser(primary, RuleBasedIntentParser()).parse(question, scenario)


@pytest.mark.parametrize(
    ("question", "intent", "source", "target"),
    [
        ("顧客データに到達する最も危険な経路は？", IntentType.HIGHEST_RISK_PATH, "Internet", "Customer Data"),
        ("Internet から侵入可能な経路だけ表示して", IntentType.LIST_ATTACK_PATHS, "Internet", "Customer Data"),
        ("CVE-XXXX を起点にどの資産へ横展開できる？", IntentType.BLAST_RADIUS, "CVE-XXXX", None),
        ("S3 Bucket に到達するまでに必要な権限は？", IntentType.REQUIRED_PERMISSIONS, "Internet", "S3 Bucket"),
        ("Service Account が漏洩した場合の影響範囲は？", IntentType.BLAST_RADIUS, "Service Account", None),
    ],
)
def test_rule_parser_handles_design_questions(question, intent, source, target):
    result = _parse(question)
    assert (result.intent, result.source, result.target) == (intent, source, target)
    assert result.parsed_by == "rule"


def test_rule_parser_two_labels_become_source_and_target():
    result = _parse("Web Server から S3 Bucket までの経路")
    assert (result.source, result.target) == ("Web Server", "S3 Bucket")


def test_classify_defaults_to_highest_risk():
    assert classify_intent("どうなってる？") == IntentType.HIGHEST_RISK_PATH


def test_llm_output_is_used_when_valid():
    llm = FakeLLM('{"intent": "blast_radius", "source": "Service Account", "target": null, "max_depth": 2}')
    result = _parse("SAが漏れたら？", llm=llm)
    assert (result.intent, result.source, result.target) == (IntentType.BLAST_RADIUS, "Service Account", None)
    assert result.max_depth == 8  # depth is never taken from the LLM
    assert result.parsed_by == "llm"
    assert "Service Account (Identity)" in llm.prompts[0]


def test_labels_in_question_override_llm_endpoints():
    llm = FakeLLM('{"intent": "blast_radius", "source": "Internet", "target": "Customer Data"}')
    result = _parse("Service Account が漏洩した場合の影響範囲は？", llm=llm)
    assert (result.source, result.target, result.parsed_by) == ("Service Account", None, "llm")


@pytest.mark.parametrize("reply", [LLMError("down"), "not json", '{"intent": "drop_database"}', '{"source": 1}'])
def test_invalid_llm_output_falls_back_to_rules(reply):
    result = _parse("顧客データに到達する最も危険な経路は？", llm=FakeLLM(reply))
    assert result.parsed_by == "rule"
    assert result.target == "Customer Data"


def test_llm_cannot_choose_edge_types():
    llm = FakeLLM('{"intent": "find_highest_risk_path", "path_types": ["HAS_PERMISSION"]}')
    assert _parse("q", llm=llm).path_types == list(ATTACK_EDGE_TYPES)


def test_guardrails_replace_hallucinated_labels_with_defaults():
    intent = Intent(source="Mainframe", target="Payroll")
    guarded = apply_guardrails(intent, A)
    assert (guarded.source, guarded.target) == ("Internet", "Customer Data")


def test_guardrails_drop_non_attack_edges():
    intent = Intent(path_types=[EdgeType.HAS_PERMISSION, EdgeType.STORES])
    assert apply_guardrails(intent, A).path_types == [EdgeType.STORES]


def test_guardrails_keep_target_empty_for_blast_radius():
    intent = Intent(intent=IntentType.BLAST_RADIUS, source="Service Account")
    assert apply_guardrails(intent, A).target is None
