from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.models.ontology import ATTACK_EDGE_TYPES, EdgeType, NodeType
from backend.models.schemas import Edge, Graph, Node, Scenario
from backend.services.seed_loader import load_all_scenarios, load_scenario


def _node(id_: str, label: str = "x", type_: str = "Asset", **extra) -> dict:
    return {"id": id_, "label": label, "type": type_, **extra}


def test_node_keeps_extra_attributes():
    node = Node(**_node("v", type_="Vulnerability", severity=9.1))
    assert node.attr("severity") == 9.1
    assert node.model_dump()["severity"] == 9.1


def test_node_rejects_unknown_type():
    with pytest.raises(ValidationError):
        Node(**_node("x", type_="Printer"))


def test_edge_rejects_unknown_type():
    with pytest.raises(ValidationError):
        Edge(source="a", target="b", type="PWNS")


def test_graph_rejects_duplicate_ids():
    with pytest.raises(ValidationError, match="duplicate"):
        Graph(nodes=[_node("a"), _node("a")])


def test_graph_rejects_dangling_edge():
    with pytest.raises(ValidationError, match="unknown nodes"):
        Graph(nodes=[_node("a")], edges=[{"source": "a", "target": "zz", "type": "HOSTS"}])


def test_scenario_requires_default_labels_in_graph():
    graph = Graph(nodes=[_node("a", label="Internet", type_="NetworkZone")])
    with pytest.raises(ValidationError, match="default label"):
        Scenario(id="s", name="s", default_source="Internet", default_target="Missing", graph=graph)


def test_attack_edges_exclude_state_edges():
    assert EdgeType.HAS_PERMISSION not in ATTACK_EDGE_TYPES
    assert EdgeType.STORES in ATTACK_EDGE_TYPES


def test_load_all_bundled_scenarios():
    scenarios = load_all_scenarios()
    assert set(scenarios) == {"demo_company_a", "demo_company_b", "demo_company_c"}


def test_node_ids_unique_across_scenarios():
    scenarios = load_all_scenarios()
    ids = [n.id for s in scenarios.values() for n in s.graph.nodes]
    assert len(ids) == len(set(ids))


def test_scenario_a_matches_design_path():
    scenario = load_all_scenarios()["demo_company_a"]
    labels = {n.label for n in scenario.graph.nodes}
    assert {"Internet", "Web Server", "CVE-XXXX", "Service Account", "S3 Bucket", "Customer Data"} <= labels


def test_all_node_types_used():
    scenarios = load_all_scenarios()
    used = {n.type for s in scenarios.values() for n in s.graph.nodes}
    assert used == set(NodeType)


def test_load_scenario_from_custom_file(tmp_path: Path):
    path = tmp_path / "s.yaml"
    path.write_text(
        "scenario: {id: t, name: T, default_source: A, default_target: B}\n"
        "nodes:\n"
        "  - {id: a, type: NetworkZone, label: A}\n"
        "  - {id: b, type: Data, label: B, confidentiality_impact: 3}\n"
        "edges:\n"
        "  - {source: a, target: b, type: CAN_REACH}\n",
        encoding="utf-8",
    )
    scenario = load_scenario(path)
    assert scenario.graph.node_by_id()["b"].attr("confidentiality_impact") == 3
