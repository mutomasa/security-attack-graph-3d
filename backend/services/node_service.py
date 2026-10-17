"""Node detail lookups for the detail panel (design §12.3)."""

from backend.models.schemas import Graph, NodeDetail
from backend.services.graph_service import GraphRepository


def find_node_detail(repo: GraphRepository, node_id: str, scenario_id: str | None = None) -> NodeDetail | None:
    candidates = [scenario_id] if scenario_id else repo.list_scenario_ids()
    for sid in candidates:
        graph = repo.get_graph(sid)
        if graph and node_id in graph.node_by_id():
            return build_node_detail(graph, node_id, sid)
    return None


def build_node_detail(graph: Graph, node_id: str, scenario_id: str) -> NodeDetail:
    nodes = graph.node_by_id()
    outgoing = [e for e in graph.edges if e.source == node_id]
    incoming = [e for e in graph.edges if e.target == node_id]
    neighbor_ids = dict.fromkeys([e.target for e in outgoing] + [e.source for e in incoming])
    return NodeDetail(
        node=nodes[node_id],
        scenario_id=scenario_id,
        outgoing=outgoing,
        incoming=incoming,
        neighbors=[nodes[i] for i in neighbor_ids],
    )
