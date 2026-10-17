import pytest

from backend.models.schemas import PathQuery
from backend.services.cypher_builder import build_path_query
from backend.services.cypher_guard import UnsafeCypherError, validate_read_only_cypher

DESIGN_QUERY = """
MATCH p = (start:NetworkZone {label: "Internet"})
  -[:EXPOSED_TO|HAS_VULNERABILITY|LEADS_TO|CAN_ACCESS|STORES*1..8]->
  (target:Data {label: "Customer Data"})
RETURN p
LIMIT 20
"""


def test_design_doc_query_is_allowed():
    validate_read_only_cypher(DESIGN_QUERY)


@pytest.mark.parametrize("target_kwargs", [{"target": "Customer Data"}, {"target_types": ["Data", "Asset"]}])
def test_generated_queries_are_allowed(target_kwargs):
    validate_read_only_cypher(build_path_query(PathQuery(scenario_id="s", source="x", **target_kwargs)).text)


def test_keywords_inside_string_literals_are_ignored():
    validate_read_only_cypher('MATCH (n:Asset {label: "DELETE ME; CREATE"}) RETURN n')


@pytest.mark.parametrize(
    "cypher",
    [
        "MATCH (n) DETACH DELETE n",
        "CREATE (n:Asset {id: 'x'})",
        "MATCH (n) SET n.pwned = true",
        "MERGE (n:Asset {id: 'x'})",
        "MATCH (n) RETURN n; MATCH (m) DELETE m",
        "CALL dbms.security.listUsers()",
        "LOAD CSV FROM 'http://evil' AS row RETURN row",
        "MATCH (n:User) RETURN n",
        "MATCH (a)-[:OWNS]->(b) RETURN b",
        "MATCH p=(a)-[*]->(b) RETURN p",
        "MATCH p=(a)-[*2..]->(b) RETURN p",
        "MATCH p=(a)-[:LEADS_TO*1..50]->(b) RETURN p",
        "MATCH p=(a)-[:LEADS_TO*20]->(b) RETURN p",
    ],
)
def test_unsafe_queries_are_rejected(cypher):
    with pytest.raises(UnsafeCypherError):
        validate_read_only_cypher(cypher)
