from app.components.presenters import (
    breakdown_rows,
    node_attribute_rows,
    node_options,
    path_rows,
    path_text,
    relation_rows,
)
from backend.models.schemas import AttackPath, Node, NodeDetail

PATH = AttackPath(
    score=10.5,
    score_breakdown={"Asset": 5, "length_penalty": -2},
    nodes=[{"id": "a", "label": "A", "type": "NetworkZone"}, {"id": "b", "label": "B", "type": "Asset"},
           {"id": "c", "label": "C", "type": "Data", "confidentiality_impact": 5}],
    edges=[{"source": "a", "target": "b", "type": "EXPOSED_TO"}, {"source": "b", "target": "c", "type": "STORES"}],
)


def test_path_text_and_rows():
    assert path_text(PATH) == "A → B → C"
    assert path_rows([PATH]) == [{"rank": 1, "score": 10.5, "hops": 2, "path": "A → B → C"}]


def test_breakdown_rows():
    assert breakdown_rows(PATH) == [{"factor": "Asset", "value": 5}, {"factor": "length_penalty", "value": -2}]


def test_node_attribute_rows_include_extras():
    rows = node_attribute_rows(PATH.nodes[2])
    assert {"attribute": "confidentiality_impact", "value": "5"} in rows


def test_relation_rows():
    detail = NodeDetail(node=PATH.nodes[1], scenario_id="s", outgoing=[PATH.edges[1]], incoming=[PATH.edges[0]],
                        neighbors=[PATH.nodes[2], PATH.nodes[0]])
    assert relation_rows(detail) == [
        {"direction": "→", "edge": "STORES", "node": "C"},
        {"direction": "←", "edge": "EXPOSED_TO", "node": "A"},
    ]


def test_node_options_put_path_nodes_first():
    extra = Node(id="z", label="Z", type="Asset")
    opts = node_options([extra, *PATH.nodes], preferred=PATH.nodes[1:])
    assert [o[0] for o in opts] == ["b", "c", "z", "a"]
