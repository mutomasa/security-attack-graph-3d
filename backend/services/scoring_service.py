"""Path risk scoring (design §9.2).

Path Risk Score =
    ( Σ(Vulnerability Severity × Exploitability)
    + max(Identity Privilege Weight)
    + max(Data Sensitivity Weight)
    + max(Asset Criticality) ) × Π(edge weight)
    - Path Length Penalty × (#edges)

The design doc sums every term, but summing impact terms rewards detours through extra
assets (see issue on scoring). Impact is therefore aggregated with max: what matters is the
highest privilege / most critical asset reached, not how many were passed through.
Edge weights (default 1.0) express how easy each step is; lowering one dampens the whole path.
"""

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from math import prod

from backend.models.ontology import NodeType
from backend.models.schemas import AttackPath, Node, PathCandidate

NodeScorer = Callable[[Node], float]
Aggregator = Callable[[list[float]], float]


def vulnerability_score(node: Node) -> float:
    return float(node.attr("severity", 0.0)) * float(node.attr("exploitability", 1.0))


def identity_score(node: Node) -> float:
    return float(node.attr("privilege", 1))


def data_score(node: Node) -> float:
    return float(node.attr("confidentiality_impact", 1))


def asset_score(node: Node) -> float:
    return float(node.attr("criticality", 1))


DEFAULT_SCORERS: dict[NodeType, NodeScorer] = {
    NodeType.VULNERABILITY: vulnerability_score,
    NodeType.IDENTITY: identity_score,
    NodeType.DATA: data_score,
    NodeType.ASSET: asset_score,
}


DEFAULT_AGGREGATORS: dict[NodeType, Aggregator] = {
    NodeType.VULNERABILITY: sum,
    NodeType.IDENTITY: max,
    NodeType.DATA: max,
    NodeType.ASSET: max,
}


@dataclass
class RiskScorer:
    scorers: dict[NodeType, NodeScorer] = field(default_factory=lambda: dict(DEFAULT_SCORERS))
    aggregators: dict[NodeType, Aggregator] = field(default_factory=lambda: dict(DEFAULT_AGGREGATORS))
    length_penalty: float = 1.0

    def score(self, path: PathCandidate) -> AttackPath:
        breakdown = self._breakdown(path)
        ease = prod(e.weight for e in path.edges)
        penalty = self.length_penalty * len(path.edges)
        total = sum(breakdown.values()) * ease - penalty
        breakdown["edge_ease"] = ease
        breakdown["length_penalty"] = -penalty
        return AttackPath(**path.model_dump(), score=round(total, 2), score_breakdown=_rounded(breakdown))

    def _breakdown(self, path: PathCandidate) -> dict[str, float]:
        values: dict[NodeType, list[float]] = defaultdict(list)
        for node in path.nodes:
            scorer = self.scorers.get(node.type)
            if scorer:
                values[node.type].append(scorer(node))
        return {t.value: self.aggregators.get(t, sum)(v) for t, v in values.items()}


def _rounded(values: dict[str, float]) -> dict[str, float]:
    return {k: round(v, 2) for k, v in values.items()}
