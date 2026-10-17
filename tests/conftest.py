import pytest

from backend.config import neo4j_settings
from backend.models.schemas import Graph, Scenario
from backend.services.graph_service import InMemoryGraphRepository, Neo4jGraphRepository

TEST_SCENARIO_ID = "pytest_scenario"


@pytest.fixture
def tiny_scenario() -> Scenario:
    graph = Graph(
        nodes=[
            {"id": "t_net", "label": "Internet", "type": "NetworkZone"},
            {"id": "t_web", "label": "Web", "type": "Asset", "criticality": 4},
            {"id": "t_cve", "label": "CVE-1", "type": "Vulnerability", "severity": 9.0, "exploitability": 0.9},
            {"id": "t_data", "label": "Customer Data", "type": "Data", "confidentiality_impact": 5},
        ],
        edges=[
            {"source": "t_net", "target": "t_web", "type": "EXPOSED_TO"},
            {"source": "t_web", "target": "t_cve", "type": "HAS_VULNERABILITY"},
            {"source": "t_cve", "target": "t_data", "type": "LEADS_TO", "weight": 0.5},
        ],
    )
    return Scenario(
        id=TEST_SCENARIO_ID, name="tiny", default_source="Internet", default_target="Customer Data", graph=graph
    )


def _neo4j_repo_or_skip() -> Neo4jGraphRepository:
    repo = Neo4jGraphRepository.from_settings(neo4j_settings())
    try:
        repo._driver.verify_connectivity()
    except Exception as exc:  # noqa: BLE001
        repo.close()
        pytest.skip(f"Neo4j not available: {exc}")
    return repo


@pytest.fixture(params=["memory", pytest.param("neo4j", marks=pytest.mark.neo4j)])
def repo(request):
    if request.param == "memory":
        yield InMemoryGraphRepository()
        return
    neo = _neo4j_repo_or_skip()
    yield neo
    with neo._driver.session() as session:
        session.run("MATCH (n {scenario: $sid}) DETACH DELETE n", sid=TEST_SCENARIO_ID).consume()
    neo.close()
