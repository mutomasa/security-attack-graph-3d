import pytest

from backend.models.schemas import Edge, Node, PathCandidate
from backend.services.scoring_service import (
    RiskScorer,
    asset_score,
    data_score,
    identity_score,
    vulnerability_score,
)


def _n(id_, type_, **attrs) -> Node:
    return Node(id=id_, label=id_, type=type_, **attrs)


def _path(nodes: list[Node], weights: list[float] | None = None) -> PathCandidate:
    weights = weights or [1.0] * (len(nodes) - 1)
    edges = [Edge(source=a.id, target=b.id, type="LEADS_TO", weight=w) for a, b, w in zip(nodes, nodes[1:], weights)]
    return PathCandidate(nodes=nodes, edges=edges)


def test_node_scorers_use_design_attributes():
    assert vulnerability_score(_n("v", "Vulnerability", severity=9.0, exploitability=0.5)) == 4.5
    assert identity_score(_n("i", "Identity", privilege=4)) == 4
    assert data_score(_n("d", "Data", confidentiality_impact=5)) == 5
    assert asset_score(_n("a", "Asset", criticality=3)) == 3


def test_missing_attributes_fall_back_to_defaults():
    assert vulnerability_score(_n("v", "Vulnerability")) == 0.0
    assert asset_score(_n("a", "Asset")) == 1.0


def test_score_formula():
    path = _path([
        _n("z", "NetworkZone"),
        _n("a1", "Asset", criticality=4),
        _n("v1", "Vulnerability", severity=10, exploitability=0.5),
        _n("v2", "Vulnerability", severity=4, exploitability=0.5),
        _n("i", "Identity", privilege=3),
        _n("a2", "Asset", criticality=5),
        _n("d", "Data", confidentiality_impact=5),
    ])
    result = RiskScorer(length_penalty=1.0).score(path)
    # vulns summed (5 + 2), impacts maxed (3 + 5 + 5), 6 edges
    assert result.score == pytest.approx(7 + 3 + 5 + 5 - 6)
    assert result.score_breakdown["Vulnerability"] == 7
    assert result.score_breakdown["Asset"] == 5
    assert result.score_breakdown["length_penalty"] == -6


def test_edge_weights_dampen_score():
    nodes = [_n("z", "NetworkZone"), _n("d", "Data", confidentiality_impact=4)]
    easy = RiskScorer(length_penalty=0).score(_path(nodes, [1.0]))
    hard = RiskScorer(length_penalty=0).score(_path(nodes, [0.5]))
    assert hard.score == easy.score / 2


def test_detour_through_extra_asset_does_not_raise_score():
    zone, data = _n("z", "NetworkZone"), _n("d", "Data", confidentiality_impact=5)
    direct = _path([zone, _n("a", "Asset", criticality=5), data])
    detour = _path([zone, _n("a", "Asset", criticality=5), _n("b", "Asset", criticality=4), data])
    scorer = RiskScorer()
    assert scorer.score(direct).score > scorer.score(detour).score


def test_custom_scorer_can_be_injected():
    scorer = RiskScorer(scorers={"Permission": lambda n: 10.0}, length_penalty=0)
    path = _path([_n("z", "NetworkZone"), _n("p", "Permission")])
    assert scorer.score(path).score == 10.0
