"""Explain an attack path in Japanese.

The template summary is always produced and is faithful to the graph. The LLM explanation is an
optional, clearly separated add-on: small models paraphrase freely and can hallucinate (issue #7).
"""

import logging
from typing import Protocol

from backend.models.ontology import EdgeType, NodeType
from backend.models.schemas import AttackPath, Node
from backend.services.llm_service import LLMClient, LLMError, load_prompt, render_prompt

logger = logging.getLogger(__name__)

STEP_PHRASES: dict[EdgeType, str] = {
    EdgeType.EXPOSED_TO: "{src} から公開された {tgt} に到達し",
    EdgeType.HAS_VULNERABILITY: "{src} の脆弱性 {tgt} を悪用し",
    EdgeType.CAN_EXPLOIT: "{tgt} を侵害し",
    EdgeType.LEADS_TO: "{tgt} を奪取し",
    EdgeType.USES_SECRET: "{src} が使う {tgt} を入手し",
    EdgeType.CAN_ACCESS: "{src} の権限で {tgt} にアクセスし",
    EdgeType.HOSTS: "{src} 上の {tgt} へ移動し",
    EdgeType.CAN_REACH: "{tgt} へネットワーク的に到達し",
    EdgeType.STORES: "{tgt} に到達する",
}

# LEADS_TO is generic; its wording depends on what the attacker progressed to.
LEADS_TO_PHRASES: dict[NodeType, str] = {
    NodeType.VULNERABILITY: "{tgt} を突き",
    NodeType.ATTACK_TECHNIQUE: "{tgt} を行い",
    NodeType.SECRET: "{tgt} を入手し",
    NodeType.IDENTITY: "{tgt} を奪取し",
    NodeType.ASSET: "{tgt} を侵害し",
    NodeType.DATA: "{tgt} に到達する",
}


class Summarizer(Protocol):
    def summarize(self, question: str, path: AttackPath | None) -> str: ...


class TemplateSummarizer:
    def summarize(self, question: str, path: AttackPath | None) -> str:
        if path is None:
            return "条件に合う攻撃経路は見つかりませんでした。"
        steps = describe_steps(path)
        start = path.nodes[0].label
        if start not in steps[0]:
            steps.insert(0, f"{start} を起点に")
        return f"最も危険な経路（スコア {path.score}）は、" + "、".join(steps) + "経路です。"


# Share of path node labels an LLM explanation must quote verbatim; below this it has drifted
# (translated names, generic advice) and is discarded.
MIN_LABEL_COVERAGE = 0.5


class LLMSummarizer:
    def __init__(self, llm: LLMClient, min_label_coverage: float = MIN_LABEL_COVERAGE) -> None:
        self._llm = llm
        self._template = load_prompt("summary_prompt.txt")
        self._min_coverage = min_label_coverage

    def summarize(self, question: str, path: AttackPath | None) -> str:
        if path is None:
            return TemplateSummarizer().summarize(question, path)
        prompt = render_prompt(self._template, question=question, score=path.score, path=format_path(path))
        text = self._llm.complete(prompt, max_tokens=300).strip()
        coverage = label_coverage(text, path)
        if coverage < self._min_coverage:
            raise LLMError(f"explanation quotes only {coverage:.0%} of path labels")
        return text


class SafeSummarizer:
    """Wrap an LLM summarizer so that failures yield None instead of breaking the query."""

    def __init__(self, inner: Summarizer) -> None:
        self._inner = inner

    def summarize(self, question: str, path: AttackPath | None) -> str | None:
        try:
            return self._inner.summarize(question, path)
        except LLMError as exc:
            logger.warning("LLM explanation failed: %s", exc)
            return None


def describe_steps(path: AttackPath) -> list[str]:
    by_id = {n.id: n for n in path.nodes}
    steps = [_phrase(e.type, by_id[e.source], by_id[e.target]) for e in path.edges]
    if steps and not steps[-1].endswith("する"):
        steps[-1] = steps[-1].removesuffix("し") + "する"
    return steps


def _phrase(edge_type: EdgeType, src: Node, tgt: Node) -> str:
    template = STEP_PHRASES.get(edge_type, "{tgt} へ進み")
    if edge_type == EdgeType.LEADS_TO:
        template = LEADS_TO_PHRASES.get(tgt.type, template)
    return template.format(src=src.label, tgt=tgt.label)


def label_coverage(text: str, path: AttackPath) -> float:
    labels = {n.label for n in path.nodes}
    return sum(label in text for label in labels) / len(labels)


def format_path(path: AttackPath) -> str:
    parts = [f"{path.nodes[0].label}({path.nodes[0].type.value})"]
    for edge, node in zip(path.edges, path.nodes[1:]):
        parts.append(f" -[{edge.type.value}]-> {node.label}({node.type.value})")
    return "".join(parts)
