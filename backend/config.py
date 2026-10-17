"""Runtime settings read from environment variables."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Neo4jSettings:
    uri: str
    user: str
    password: str


def neo4j_settings() -> Neo4jSettings:
    return Neo4jSettings(
        uri=os.environ.get("NEO4J_URI", "bolt://localhost:17687"),
        user=os.environ.get("NEO4J_USER", "neo4j"),
        password=os.environ.get("NEO4J_PASSWORD", "attackgraph"),
    )


def graph_backend() -> str:
    """'neo4j' or 'memory'."""
    return os.environ.get("GRAPH_BACKEND", "neo4j")
