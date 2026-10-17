"""networkx-based path search used by the in-memory repository (mirrors the Cypher semantics)."""

from itertools import islice

import networkx as nx

from backend.models.schemas import Edge, Graph, Node, PathCandidate, PathQuery


def find_paths_in_graph(graph: Graph, query: PathQuery) -> list[PathCandidate]:
    nodes = graph.node_by_id()
    digraph = _to_multidigraph(graph, query)
    sources = _match_nodes(nodes.values(), lambda n: _matches_ref(n, query.source))
    targets = _match_nodes(nodes.values(), lambda n: _is_target(n, query))
    paths = _simple_edge_paths(digraph, sources, targets, query.max_depth)
    return [_to_candidate(p, digraph, nodes) for p in islice(paths, query.candidate_limit)]


def _to_multidigraph(graph: Graph, query: PathQuery) -> nx.MultiDiGraph:
    allowed = set(query.edge_types)
    digraph = nx.MultiDiGraph()
    digraph.add_nodes_from(n.id for n in graph.nodes)
    for edge in graph.edges:
        if edge.type in allowed:
            digraph.add_edge(edge.source, edge.target, key=edge.type.value, edge=edge)
    return digraph


def _match_nodes(nodes, predicate) -> list[str]:
    return [n.id for n in nodes if predicate(n)]


def _matches_ref(node: Node, ref: str) -> bool:
    return ref in (node.label, node.id)


def _is_target(node: Node, query: PathQuery) -> bool:
    if query.target:
        return _matches_ref(node, query.target)
    return node.type in query.target_types


def _simple_edge_paths(digraph: nx.MultiDiGraph, sources: list[str], targets: list[str], cutoff: int):
    for source in sources:
        reachable = [t for t in targets if t != source]
        if reachable:
            yield from nx.all_simple_edge_paths(digraph, source, reachable, cutoff=cutoff)


def _to_candidate(
    edge_path: list[tuple[str, str, str]], digraph: nx.MultiDiGraph, nodes: dict[str, Node]
) -> PathCandidate:
    edges: list[Edge] = [digraph.edges[u, v, k]["edge"] for u, v, k in edge_path]
    node_ids = [edge_path[0][0]] + [v for _, v, _ in edge_path]
    return PathCandidate(nodes=[nodes[i] for i in node_ids], edges=edges)
