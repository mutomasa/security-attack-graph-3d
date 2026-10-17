import pytest

from backend.models.schemas import AttackPath, PathQuery
from backend.services.cypher_builder import build_path_query
from backend.services.path_service import AttackPathService, rank_paths
from backend.services.seeder import seed_repository
from tests.conftest import TEST_SCENARIO_ID


def _labels(path) -> list[str]:
    return [n.label for n in path.nodes]


@pytest.fixture
def seeded(repo):
    seed_repository(repo)
    return repo


@pytest.mark.parametrize(
    ("scenario", "source", "target", "expected"),
    [
        ("demo_company_a", "Internet", "Customer Data",
         ["Internet", "Web Server", "CVE-XXXX", "Credential Leak", "Service Account", "S3 Bucket", "Customer Data"]),
        ("demo_company_b", "Internet", "Customer Data",
         ["Internet", "GitHub Repo", "Hardcoded Secret", "CI Deploy API Key", "Cloud Deploy Role", "Customer DB",
          "Customer Data"]),
        ("demo_company_c", "Internal User", "Sensitive Table",
         ["Internal User", "Excessive Trust Policy", "Privilege Escalation", "Over-privileged Role", "Data Lake",
          "Sensitive Table"]),
    ],
)
def test_top_path_matches_scenario_story(seeded, scenario, source, target, expected):
    paths = AttackPathService(seeded).find_top_paths(PathQuery(scenario_id=scenario, source=source, target=target))
    assert _labels(paths[0]) == expected


def test_memory_and_cypher_find_same_paths(repo, tiny_scenario):
    repo.save_scenario(tiny_scenario)
    paths = repo.find_paths(PathQuery(scenario_id=TEST_SCENARIO_ID, source="Internet", target="Customer Data"))
    assert [[n.id for n in p.nodes] for p in paths] == [["t_net", "t_web", "t_cve", "t_data"]]
    assert paths[0].edges[-1].weight == 0.5


def test_paths_are_node_simple(seeded):
    query = PathQuery(scenario_id="demo_company_b", source="Internet", target="Customer Data", max_depth=10)
    for path in seeded.find_paths(query):
        ids = [n.id for n in path.nodes]
        assert len(ids) == len(set(ids))


def test_max_depth_limits_path_length(seeded):
    query = PathQuery(scenario_id="demo_company_a", source="Internet", target="Customer Data", max_depth=5)
    paths = seeded.find_paths(query)
    assert paths and all(len(p.edges) <= 5 for p in paths)


def test_edge_type_filter(seeded):
    query = PathQuery(
        scenario_id="demo_company_a", source="Internet", target="Customer Data",
        edge_types=["EXPOSED_TO", "HAS_VULNERABILITY", "LEADS_TO", "CAN_ACCESS", "STORES"],
    )
    paths = seeded.find_paths(query)
    assert paths
    assert all(e.type.value != "CAN_EXPLOIT" for p in paths for e in p.edges)


def test_target_types_without_target_finds_blast_radius(seeded):
    query = PathQuery(scenario_id="demo_company_a", source="Service Account", target_types=["Data", "Asset"])
    reached = {p.nodes[-1].label for p in seeded.find_paths(query)}
    assert reached == {"S3 Bucket", "Customer Data"}


def test_unknown_scenario_returns_no_paths(seeded):
    assert seeded.find_paths(PathQuery(scenario_id="nope", source="Internet")) == []


def _ap(score, n_nodes):
    nodes = [{"id": f"n{i}", "label": f"n{i}", "type": "Asset"} for i in range(n_nodes)]
    edges = [{"source": f"n{i}", "target": f"n{i + 1}", "type": "LEADS_TO"} for i in range(n_nodes - 1)]
    return AttackPath(score=score, nodes=nodes, edges=edges)


def test_rank_paths_orders_filters_and_truncates():
    paths = [_ap(5, 3), _ap(9, 4), _ap(9, 3), _ap(1, 2)]
    ranked = rank_paths(paths, top_n=2, min_score=2)
    assert [(p.score, len(p.edges)) for p in ranked] == [(9, 2), (9, 3)]


def test_cypher_builder_parameterises_user_values():
    query = PathQuery(scenario_id="s", source='x" OR 1=1', target="Customer Data", max_depth=4,
                      edge_types=["EXPOSED_TO", "STORES"])
    cypher = build_path_query(query)
    assert "[:EXPOSED_TO|STORES*1..4]" in cypher.text
    assert 'x"' not in cypher.text
    assert cypher.params["source"] == 'x" OR 1=1'


def test_cypher_display_inlines_params():
    cypher = build_path_query(PathQuery(scenario_id="s", source="Internet", target_types=["Data"]))
    shown = cypher.display()
    assert '"Internet"' in shown and '["Data"]' in shown and "$" not in shown
