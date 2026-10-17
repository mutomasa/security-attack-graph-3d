"""Attack Path Engine: search candidates, score them and return the top N."""

from backend.models.schemas import AttackPath, PathQuery
from backend.services.graph_service import GraphRepository
from backend.services.scoring_service import RiskScorer


class AttackPathService:
    def __init__(self, repo: GraphRepository, scorer: RiskScorer | None = None) -> None:
        self._repo = repo
        self._scorer = scorer or RiskScorer()

    def find_top_paths(self, query: PathQuery) -> list[AttackPath]:
        scored = [self._scorer.score(c) for c in self._repo.find_paths(query)]
        return rank_paths(scored, query.top_n, query.min_score)


def rank_paths(paths: list[AttackPath], top_n: int, min_score: float = 0.0) -> list[AttackPath]:
    kept = [p for p in paths if p.score >= min_score]
    # Ties: prefer the shorter path, then a stable textual order for deterministic output.
    kept.sort(key=lambda p: (-p.score, len(p.edges), [n.id for n in p.nodes]))
    return kept[:top_n]
