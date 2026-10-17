"""Turn a graph + ranked attack paths into the JSON the Three.js viewer renders.

Layout is layered: x follows the attack progression (BFS depth from the scenario's entry point),
nodes in the same layer are spread on a circle in the y/z plane.
"""

import math
from collections import deque

from backend.models.ontology import NodeType
from backend.models.schemas import AttackPath, Edge, Graph, Node

NODE_STYLES: dict[NodeType, dict[str, str]] = {
    NodeType.ASSET: {"color": "#3b82f6", "shape": "sphere"},
    NodeType.VULNERABILITY: {"color": "#ef4444", "shape": "octahedron"},
    NodeType.IDENTITY: {"color": "#a855f7", "shape": "cube"},
    NodeType.PERMISSION: {"color": "#eab308", "shape": "cylinder"},
    NodeType.SECRET: {"color": "#f97316", "shape": "tetrahedron"},
    NodeType.DATA: {"color": "#22c55e", "shape": "glow_sphere"},
    NodeType.NETWORK_ZONE: {"color": "#9ca3af", "shape": "torus"},
    NodeType.ATTACK_TECHNIQUE: {"color": "#ec4899", "shape": "cone"},
}

LAYER_SPACING = 6.0
RING_RADIUS = 3.5
# Rotate each layer's ring so nodes of neighbouring layers do not line up behind each other.
RING_PHASE_STEP = 0.9

Position = tuple[float, float, float]


def build_view_model(graph: Graph, paths: list[AttackPath], entry: str | None = None) -> dict:
    ranks = path_edge_ranks(paths)
    on_path = path_node_ids(paths[:1])
    positions = layered_layout(graph, entry)
    return {
        "nodes": [_node_view(n, positions[n.id], n.id in on_path) for n in graph.nodes],
        "edges": [_edge_view(e, ranks.get(_edge_key(e))) for e in graph.edges],
        "paths": [[n.id for n in p.nodes] for p in paths],
    }


def path_edge_ranks(paths: list[AttackPath]) -> dict[tuple[str, str, str], int]:
    """Edge -> best (lowest) rank of a path that uses it. Rank 0 is the top path."""
    ranks: dict[tuple[str, str, str], int] = {}
    for rank, path in enumerate(paths):
        for edge in path.edges:
            ranks.setdefault(_edge_key(edge), rank)
    return ranks


def path_node_ids(paths: list[AttackPath]) -> set[str]:
    return {n.id for p in paths for n in p.nodes}


def layered_layout(graph: Graph, entry: str | None = None) -> dict[str, Position]:
    depths = bfs_depths(graph, _entry_ids(graph, entry))
    layers = _group_by_layer(graph.nodes, depths)
    offset = (min(layers) + max(layers)) * LAYER_SPACING / 2
    positions: dict[str, Position] = {}
    for depth, node_ids in sorted(layers.items()):
        for node_id, (y, z) in zip(node_ids, _ring(len(node_ids), phase=depth * RING_PHASE_STEP)):
            positions[node_id] = (round(depth * LAYER_SPACING - offset, 3), y, z)
    return positions


def bfs_depths(graph: Graph, start_ids: list[str]) -> dict[str, int]:
    adjacency: dict[str, list[str]] = {n.id: [] for n in graph.nodes}
    for edge in graph.edges:
        adjacency[edge.source].append(edge.target)
    depths = {s: 0 for s in start_ids}
    queue = deque(start_ids)
    while queue:
        current = queue.popleft()
        for nxt in adjacency[current]:
            if nxt not in depths:
                depths[nxt] = depths[current] + 1
                queue.append(nxt)
    return depths


def _entry_ids(graph: Graph, entry: str | None) -> list[str]:
    if entry:
        hits = [n.id for n in graph.nodes if entry in (n.id, n.label)]
        if hits:
            return hits
    targets = {e.target for e in graph.edges}
    return [n.id for n in graph.nodes if n.id not in targets]


def _group_by_layer(nodes: list[Node], depths: dict[str, int]) -> dict[int, list[str]]:
    """Unreachable nodes (e.g. zones that only HOST things) go one layer before the entry."""
    layers: dict[int, list[str]] = {}
    for node in nodes:
        layers.setdefault(depths.get(node.id, -1), []).append(node.id)
    return layers


def _ring(count: int, phase: float = 0.0) -> list[tuple[float, float]]:
    if count == 1:
        return [(0.0, 0.0)]
    radius = RING_RADIUS * (1 + count / 8)
    angles = [phase + 2 * math.pi * i / count for i in range(count)]
    return [(round(radius * math.cos(a), 3), round(radius * math.sin(a), 3)) for a in angles]


def _node_view(node: Node, pos: Position, on_top_path: bool) -> dict:
    return {
        "id": node.id,
        "label": node.label,
        "type": node.type.value,
        **NODE_STYLES[node.type],
        "pos": list(pos),
        "onPath": on_top_path,
        "attrs": node.model_extra or {},
    }


def _edge_view(edge: Edge, rank: int | None) -> dict:
    return {"source": edge.source, "target": edge.target, "type": edge.type.value, "pathRank": rank}


def _edge_key(edge: Edge) -> tuple[str, str, str]:
    return (edge.source, edge.target, edge.type.value)
