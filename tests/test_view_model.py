import json

from app.components.graph_viewer import render_graph_html
from app.components.view_model import (
    NODE_STYLES,
    bfs_depths,
    build_view_model,
    layered_layout,
    path_edge_ranks,
)
from backend.models.ontology import NodeType
from backend.models.schemas import Graph, PathQuery
from backend.services.graph_service import InMemoryGraphRepository
from backend.services.path_service import AttackPathService
from backend.services.seeder import seed_repository


def _scenario_a():
    repo = InMemoryGraphRepository()
    seed_repository(repo)
    graph = repo.get_graph("demo_company_a")
    paths = AttackPathService(repo).find_top_paths(
        PathQuery(scenario_id="demo_company_a", source="Internet", target="Customer Data"))
    return graph, paths


def _chain() -> Graph:
    return Graph(
        nodes=[{"id": i, "label": i.upper(), "type": "Asset"} for i in "abcd"],
        edges=[{"source": "a", "target": "b", "type": "CAN_REACH"},
               {"source": "b", "target": "c", "type": "CAN_REACH"},
               {"source": "a", "target": "c", "type": "CAN_REACH"}],
    )


def test_every_node_type_has_design_color():
    assert set(NODE_STYLES) == set(NodeType)
    assert NODE_STYLES[NodeType.VULNERABILITY]["color"] == "#ef4444"
    assert NODE_STYLES[NodeType.IDENTITY]["shape"] == "cube"


def test_bfs_depth_uses_shortest_hop_count():
    assert bfs_depths(_chain(), ["a"]) == {"a": 0, "b": 1, "c": 1}


def test_layout_progresses_along_x_and_places_unreachable_first():
    pos = layered_layout(_chain(), "A")
    assert pos["d"][0] < pos["a"][0] < pos["b"][0]
    assert pos["b"][0] == pos["c"][0]
    assert pos["b"][1:] != pos["c"][1:]


def test_layout_without_entry_starts_from_root_nodes():
    pos = layered_layout(_chain())
    assert pos["a"][0] == pos["d"][0] < pos["b"][0]


def test_path_edge_ranks_keep_best_rank():
    graph, paths = _scenario_a()
    ranks = path_edge_ranks(paths)
    assert ranks[("a_internet", "a_web", "EXPOSED_TO")] == 0
    assert ranks[("a_cve", "a_app", "CAN_EXPLOIT")] == 1


def test_view_model_marks_top_path():
    graph, paths = _scenario_a()
    vm = build_view_model(graph, paths, "Internet")
    on_path = {n["label"] for n in vm["nodes"] if n["onPath"]}
    assert on_path == {"Internet", "Web Server", "CVE-XXXX", "Credential Leak", "Service Account", "S3 Bucket",
                       "Customer Data"}
    assert len(vm["edges"]) == len(graph.edges)
    assert vm["paths"][0][0] == "a_internet"
    cve = next(n for n in vm["nodes"] if n["id"] == "a_cve")
    assert cve["attrs"]["severity"] == 9.1


def test_view_model_without_paths():
    graph, _ = _scenario_a()
    vm = build_view_model(graph, [])
    assert vm["paths"] == [] and all(e["pathRank"] is None for e in vm["edges"])


def test_render_embeds_data_and_script():
    graph, paths = _scenario_a()
    html = render_graph_html(build_view_model(graph, paths), height=500)
    assert "__" not in html.replace("__proto__", "")
    assert "height: 500px" in html
    assert "OrbitControls" in html
    data = html.split('<script id="graph-data" type="application/json">')[1].split("</script>")[0]
    assert len(json.loads(data)["nodes"]) == 20


def test_render_escapes_script_terminators():
    graph = Graph(nodes=[{"id": "x", "label": "</script><script>alert(1)</script>", "type": "Asset"}])
    html = render_graph_html(build_view_model(graph, []))
    assert "</script><script>alert(1)" not in html

