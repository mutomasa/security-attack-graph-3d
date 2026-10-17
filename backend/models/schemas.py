"""Pydantic schemas shared by the graph store, path engine and API."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.models.ontology import ATTACK_EDGE_TYPES, MAX_PATH_DEPTH, EdgeType, NodeType


class Node(BaseModel):
    """A graph node. Type-specific attributes (severity, criticality, ...) are kept as extras."""

    model_config = ConfigDict(extra="allow")

    id: str
    label: str
    type: NodeType

    def attr(self, name: str, default: Any = None) -> Any:
        return (self.model_extra or {}).get(name, default)


class Edge(BaseModel):
    source: str
    target: str
    type: EdgeType
    weight: float = 1.0


class Graph(BaseModel):
    nodes: list[Node] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_integrity(self) -> "Graph":
        ids = [n.id for n in self.nodes]
        _ensure_unique(ids)
        _ensure_edges_resolve(self.edges, set(ids))
        return self

    def node_by_id(self) -> dict[str, Node]:
        return {n.id: n for n in self.nodes}


class Scenario(BaseModel):
    id: str
    name: str
    description: str = ""
    default_source: str
    default_target: str
    graph: Graph

    @model_validator(mode="after")
    def _check_defaults(self) -> "Scenario":
        labels = {n.label for n in self.graph.nodes}
        for label in (self.default_source, self.default_target):
            if label not in labels:
                raise ValueError(f"default label not found in graph: {label}")
        return self


class PathQuery(BaseModel):
    """Structured search condition. Either `target` (a node label/id) or `target_types` selects the end nodes."""

    scenario_id: str
    source: str
    target: str | None = None
    target_types: list[NodeType] = Field(default_factory=lambda: [NodeType.DATA])
    edge_types: list[EdgeType] = Field(default_factory=lambda: list(ATTACK_EDGE_TYPES))
    max_depth: int = Field(default=8, ge=1, le=MAX_PATH_DEPTH)
    top_n: int = Field(default=3, ge=1, le=50)
    min_score: float = 0.0
    candidate_limit: int = Field(default=500, ge=1, le=5000)


class PathCandidate(BaseModel):
    nodes: list[Node]
    edges: list[Edge]


class AttackPath(PathCandidate):
    score: float
    score_breakdown: dict[str, float] = Field(default_factory=dict)


def _ensure_unique(ids: list[str]) -> None:
    seen: set[str] = set()
    dupes = {i for i in ids if i in seen or seen.add(i)}
    if dupes:
        raise ValueError(f"duplicate node ids: {sorted(dupes)}")


def _ensure_edges_resolve(edges: list[Edge], ids: set[str]) -> None:
    for e in edges:
        missing = {e.source, e.target} - ids
        if missing:
            raise ValueError(f"edge {e.source}->{e.target} references unknown nodes: {sorted(missing)}")
