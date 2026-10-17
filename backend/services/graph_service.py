"""Graph storage. Neo4j is the primary store; the in-memory store backs tests and offline demos."""

from collections import defaultdict
from typing import Protocol

from neo4j import Driver, GraphDatabase

from backend.config import Neo4jSettings
from backend.models.schemas import Edge, Graph, Node, Scenario


class GraphRepository(Protocol):
    def save_scenario(self, scenario: Scenario) -> None: ...

    def get_graph(self, scenario_id: str) -> Graph | None: ...

    def get_node(self, node_id: str) -> Node | None: ...

    def list_scenario_ids(self) -> list[str]: ...


class InMemoryGraphRepository:
    def __init__(self) -> None:
        self._graphs: dict[str, Graph] = {}

    def save_scenario(self, scenario: Scenario) -> None:
        self._graphs[scenario.id] = scenario.graph

    def get_graph(self, scenario_id: str) -> Graph | None:
        return self._graphs.get(scenario_id)

    def get_node(self, node_id: str) -> Node | None:
        for graph in self._graphs.values():
            node = graph.node_by_id().get(node_id)
            if node:
                return node
        return None

    def list_scenario_ids(self) -> list[str]:
        return sorted(self._graphs)


class Neo4jGraphRepository:
    """Stores each node with its ontology type as the Neo4j label and a `scenario` property."""

    def __init__(self, driver: Driver) -> None:
        self._driver = driver

    @classmethod
    def from_settings(cls, settings: Neo4jSettings) -> "Neo4jGraphRepository":
        return cls(GraphDatabase.driver(settings.uri, auth=(settings.user, settings.password)))

    def close(self) -> None:
        self._driver.close()

    def save_scenario(self, scenario: Scenario) -> None:
        with self._driver.session() as session:
            session.execute_write(_replace_scenario, scenario)

    def get_graph(self, scenario_id: str) -> Graph | None:
        with self._driver.session() as session:
            nodes, edges = session.execute_read(_read_scenario, scenario_id)
        if not nodes:
            return None
        return Graph(nodes=nodes, edges=edges)

    def get_node(self, node_id: str) -> Node | None:
        with self._driver.session() as session:
            return session.execute_read(_read_node, node_id)

    def list_scenario_ids(self) -> list[str]:
        query = "MATCH (n) WHERE n.scenario IS NOT NULL RETURN DISTINCT n.scenario AS s ORDER BY s"
        with self._driver.session() as session:
            return session.execute_read(lambda tx: [r["s"] for r in tx.run(query)])


def _replace_scenario(tx, scenario: Scenario) -> None:
    tx.run("MATCH (n {scenario: $sid}) DETACH DELETE n", sid=scenario.id)
    _create_nodes(tx, scenario.id, scenario.graph.nodes)
    _create_edges(tx, scenario.id, scenario.graph.edges)


def _create_nodes(tx, scenario_id: str, nodes: list[Node]) -> None:
    for node_type, props in _group_node_props(scenario_id, nodes).items():
        # Labels cannot be parameterised; node_type comes from the NodeType enum.
        tx.run(f"UNWIND $rows AS row CREATE (n:`{node_type}`) SET n = row", rows=props)


def _group_node_props(scenario_id: str, nodes: list[Node]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for node in nodes:
        grouped[node.type.value].append({**node.model_dump(mode="json"), "scenario": scenario_id})
    return grouped


def _create_edges(tx, scenario_id: str, edges: list[Edge]) -> None:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for edge in edges:
        grouped[edge.type.value].append(edge.model_dump(mode="json"))
    for edge_type, rows in grouped.items():
        tx.run(
            "UNWIND $rows AS row "
            "MATCH (s {id: row.source, scenario: $sid}), (t {id: row.target, scenario: $sid}) "
            f"CREATE (s)-[r:`{edge_type}`]->(t) SET r.weight = row.weight",
            rows=rows,
            sid=scenario_id,
        )


def _read_scenario(tx, scenario_id: str) -> tuple[list[Node], list[Edge]]:
    node_rows = tx.run("MATCH (n {scenario: $sid}) RETURN properties(n) AS p", sid=scenario_id)
    nodes = [record_to_node(r["p"]) for r in node_rows]
    edge_rows = tx.run(
        "MATCH (s {scenario: $sid})-[r]->(t {scenario: $sid}) "
        "RETURN s.id AS source, t.id AS target, type(r) AS type, r.weight AS weight",
        sid=scenario_id,
    )
    edges = [Edge(**r.data()) for r in edge_rows]
    return nodes, edges


def _read_node(tx, node_id: str) -> Node | None:
    record = tx.run("MATCH (n {id: $id}) RETURN properties(n) AS p LIMIT 1", id=node_id).single()
    return record_to_node(record["p"]) if record else None


def record_to_node(props: dict) -> Node:
    data = dict(props)
    data.pop("scenario", None)
    return Node(**data)
