import pytest
from fastapi.testclient import TestClient

from backend.config import LLMSettings
from backend.main import create_app
from backend.services.factory import build_query_service
from backend.services.graph_service import InMemoryGraphRepository

OFFLINE = LLMSettings(enabled=False, base_url="", model="", timeout=1)


@pytest.fixture
def client():
    repo = InMemoryGraphRepository()
    with TestClient(create_app(repo=repo, query_service=build_query_service(repo, OFFLINE))) as c:
        c.post("/seed")
        yield c


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_seed_returns_scenarios(client):
    assert client.post("/seed").json() == {"seeded": ["demo_company_a", "demo_company_b", "demo_company_c"]}


def test_query_matches_design_response_shape(client):
    res = client.post("/query", json={"question": "顧客データに到達する最も危険な経路は？", "scenario": "demo_company_a"})
    assert res.status_code == 200
    body = res.json()
    assert body["intent"] == "find_highest_risk_path"
    assert body["cypher"].startswith("MATCH p =")
    top = body["paths"][0]
    assert [n["label"] for n in top["nodes"]][:3] == ["Internet", "Web Server", "CVE-XXXX"]
    assert {"source", "target", "type"} <= set(top["edges"][0])
    assert top["nodes"][2]["severity"] == 9.1
    assert body["summary"].startswith("最も危険な経路")


def test_query_options_are_applied(client):
    res = client.post("/query", json={"question": "顧客データ", "scenario": "demo_company_a", "top_n": 1})
    assert len(res.json()["paths"]) == 1


def test_query_unknown_scenario_is_404(client):
    res = client.post("/query", json={"question": "q", "scenario": "nope"})
    assert res.status_code == 404


@pytest.mark.parametrize("payload", [{"question": "", "scenario": "demo_company_a"},
                                     {"question": "q", "scenario": "demo_company_a", "max_depth": 99},
                                     {"question": "x" * 501, "scenario": "demo_company_a"}])
def test_query_input_validation(client, payload):
    assert client.post("/query", json=payload).status_code == 422


def test_list_scenarios(client):
    ids = [s["id"] for s in client.get("/scenarios").json()]
    assert ids == ["demo_company_a", "demo_company_b", "demo_company_c"]


def test_scenario_graph(client):
    body = client.get("/graph/scenario/demo_company_b").json()
    assert body["scenario"]["default_target"] == "Customer Data"
    assert len(body["nodes"]) == 16
    assert any(e["type"] == "USES_SECRET" for e in body["edges"])


def test_scenario_graph_404(client):
    assert client.get("/graph/scenario/zzz").status_code == 404


def test_node_detail_includes_neighbors(client):
    body = client.get("/node/a_svc").json()
    assert body["node"]["label"] == "Service Account"
    assert body["scenario_id"] == "demo_company_a"
    assert {n["label"] for n in body["neighbors"]} == {"Credential Leak", "s3:GetObject", "S3 Bucket"}
    assert {e["type"] for e in body["outgoing"]} == {"HAS_PERMISSION", "CAN_ACCESS"}


def test_node_detail_with_scenario_filter(client):
    assert client.get("/node/a_svc", params={"scenario": "demo_company_b"}).status_code == 404


def test_ontology_lists_all_types(client):
    body = client.get("/ontology").json()
    assert len(body["node_types"]) == 8 and len(body["edge_types"]) == 11
