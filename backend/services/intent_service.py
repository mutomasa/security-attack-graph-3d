"""Natural language question -> Intent. LLM first, rule-based fallback, then guardrails."""

import logging
from typing import Protocol

from pydantic import ValidationError

from backend.models.ontology import ATTACK_EDGE_TYPES, MAX_PATH_DEPTH
from backend.models.schemas import Intent, IntentType, Scenario
from backend.services.llm_service import LLMClient, LLMError, extract_json_object, load_prompt, render_prompt

logger = logging.getLogger(__name__)

# Japanese phrases users are likely to type, mapped to node labels used in the seed data.
LABEL_ALIASES: dict[str, str] = {
    "顧客データ": "Customer Data",
    "顧客情報": "Customer Data",
    "インターネット": "Internet",
    "外部": "Internet",
    "サービスアカウント": "Service Account",
    "ウェブサーバ": "Web Server",
    "webサーバ": "Web Server",
    "社内ユーザー": "Internal User",
    "機密テーブル": "Sensitive Table",
    "データレイク": "Data Lake",
    "s3": "S3 Bucket",
    "api key": "CI Deploy API Key",
    "apiキー": "CI Deploy API Key",
}

INTENT_KEYWORDS: list[tuple[IntentType, tuple[str, ...]]] = [
    (IntentType.REQUIRED_PERMISSIONS, ("権限", "permission")),
    (IntentType.BLAST_RADIUS, ("影響範囲", "横展開", "漏洩した場合", "起点に", "blast")),
    (IntentType.LIST_ATTACK_PATHS, ("だけ", "一覧", "すべて", "全て", "侵入可能")),
]


class IntentParser(Protocol):
    def parse(self, question: str, scenario: Scenario) -> Intent: ...


class RuleBasedIntentParser:
    def parse(self, question: str, scenario: Scenario) -> Intent:
        intent_type = classify_intent(question)
        mentioned = find_mentioned_labels(question, scenario)
        source, target = assign_endpoints(intent_type, mentioned)
        return Intent(intent=intent_type, source=source, target=target, parsed_by="rule")


class LLMIntentParser:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm
        self._template = load_prompt("intent_prompt.txt")

    def parse(self, question: str, scenario: Scenario) -> Intent:
        prompt = self._build_prompt(scenario) + f"\n\n質問: {question}"
        raw = extract_json_object(self._llm.complete(prompt, json_mode=True))
        # Edge types are fixed by the ontology and depth by the UI; small models pick both badly.
        for key in ("path_types", "max_depth", "parsed_by"):
            raw.pop(key, None)
        return Intent(**raw, parsed_by="llm")

    def _build_prompt(self, scenario: Scenario) -> str:
        labels = "\n".join(f"- {n.label} ({n.type.value})" for n in scenario.graph.nodes)
        return render_prompt(
            self._template,
            scenario_name=scenario.name,
            default_source=scenario.default_source,
            default_target=scenario.default_target,
            labels=labels,
        )


class FallbackIntentParser:
    """Try the primary parser (LLM); on any failure use the fallback (rules). Always apply guardrails."""

    def __init__(self, primary: IntentParser | None, fallback: IntentParser) -> None:
        self._primary = primary
        self._fallback = fallback

    def parse(self, question: str, scenario: Scenario) -> Intent:
        return apply_guardrails(self._parse_raw(question, scenario), scenario)

    def _parse_raw(self, question: str, scenario: Scenario) -> Intent:
        if self._primary:
            try:
                intent = self._primary.parse(question, scenario)
                return prefer_mentioned_endpoints(intent, find_mentioned_labels(question, scenario))
            except (LLMError, ValidationError, TypeError) as exc:
                logger.warning("LLM intent parsing failed, using rules: %s", exc)
        return self._fallback.parse(question, scenario)


def classify_intent(question: str) -> IntentType:
    lowered = question.lower()
    for intent_type, keywords in INTENT_KEYWORDS:
        if any(k in lowered for k in keywords):
            return intent_type
    return IntentType.HIGHEST_RISK_PATH


def find_mentioned_labels(question: str, scenario: Scenario) -> list[str]:
    """Labels mentioned in the question, in order of appearance."""
    lowered = question.lower()
    labels = {n.label for n in scenario.graph.nodes}
    hits: dict[str, int] = {}
    for phrase, label in [(lbl.lower(), lbl) for lbl in labels] + list(LABEL_ALIASES.items()):
        pos = lowered.find(phrase)
        if pos >= 0 and label in labels:
            hits[label] = min(pos, hits.get(label, pos))
    return sorted(hits, key=hits.__getitem__)


def assign_endpoints(intent_type: IntentType, mentioned: list[str]) -> tuple[str | None, str | None]:
    if intent_type == IntentType.BLAST_RADIUS:
        return (mentioned[0] if mentioned else None), None
    if len(mentioned) >= 2:
        return mentioned[0], mentioned[-1]
    if intent_type == IntentType.LIST_ATTACK_PATHS and mentioned:
        return mentioned[0], None
    return None, (mentioned[0] if mentioned else None)


def prefer_mentioned_endpoints(intent: Intent, mentioned: list[str]) -> Intent:
    """Labels literally present in the question beat the LLM's guess; the LLM still decides the intent."""
    source, target = assign_endpoints(intent.intent, mentioned)
    if source is None and target is None:
        return intent
    update = {"source": source or intent.source, "target": target or intent.target}
    if intent.intent == IntentType.BLAST_RADIUS:
        update["target"] = None
    return intent.model_copy(update=update)


def apply_guardrails(intent: Intent, scenario: Scenario) -> Intent:
    """Snap endpoints to real labels, restrict edge types and depth (design §10.3)."""
    labels = {n.label for n in scenario.graph.nodes}
    source = intent.source if intent.source in labels else scenario.default_source
    target = intent.target if intent.target in labels else None
    if target is None and intent.intent != IntentType.BLAST_RADIUS:
        target = scenario.default_target
    allowed = [t for t in intent.path_types if t in ATTACK_EDGE_TYPES] or list(ATTACK_EDGE_TYPES)
    depth = max(1, min(intent.max_depth, MAX_PATH_DEPTH))
    return intent.model_copy(update={"source": source, "target": target, "path_types": allowed, "max_depth": depth})
