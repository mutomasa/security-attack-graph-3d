from backend.services.graph_service import InMemoryGraphRepository
from backend.services.seeder import seed_repository
from tests.conftest import TEST_SCENARIO_ID


def test_roundtrip_graph(repo, tiny_scenario):
    repo.save_scenario(tiny_scenario)
    graph = repo.get_graph(TEST_SCENARIO_ID)
    assert {n.id for n in graph.nodes} == {"t_net", "t_web", "t_cve", "t_data"}
    assert {(e.source, e.target, e.type.value) for e in graph.edges} == {
        ("t_net", "t_web", "EXPOSED_TO"),
        ("t_web", "t_cve", "HAS_VULNERABILITY"),
        ("t_cve", "t_data", "LEADS_TO"),
    }


def test_edge_weight_preserved(repo, tiny_scenario):
    repo.save_scenario(tiny_scenario)
    weights = {e.target: e.weight for e in repo.get_graph(TEST_SCENARIO_ID).edges}
    assert weights["t_data"] == 0.5


def test_get_node_keeps_attributes(repo, tiny_scenario):
    repo.save_scenario(tiny_scenario)
    node = repo.get_node("t_cve")
    assert node.type.value == "Vulnerability"
    assert node.attr("severity") == 9.0
    assert node.attr("scenario") is None


def test_unknown_lookups_return_none(repo):
    assert repo.get_graph("nope") is None
    assert repo.get_node("nope") is None


def test_save_replaces_existing_scenario(repo, tiny_scenario):
    repo.save_scenario(tiny_scenario)
    smaller = tiny_scenario.model_copy(deep=True)
    smaller.graph.edges = smaller.graph.edges[:1]
    repo.save_scenario(smaller)
    assert len(repo.get_graph(TEST_SCENARIO_ID).edges) == 1
    assert len(repo.get_graph(TEST_SCENARIO_ID).nodes) == 4


def test_list_scenarios_includes_saved(repo, tiny_scenario):
    repo.save_scenario(tiny_scenario)
    assert TEST_SCENARIO_ID in repo.list_scenario_ids()


def test_seed_repository_loads_bundled_scenarios():
    repo = InMemoryGraphRepository()
    seeded = seed_repository(repo)
    assert seeded == ["demo_company_a", "demo_company_b", "demo_company_c"]
    assert repo.get_node("a_cve").label == "CVE-XXXX"
