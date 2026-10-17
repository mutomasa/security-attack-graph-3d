from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from backend.api.deps import get_repo, get_scenarios
from backend.models.ontology import EDGE_DESCRIPTIONS, NODE_DESCRIPTIONS
from backend.models.schemas import NodeDetail, Scenario, ScenarioGraph, ScenarioSummary
from backend.services.graph_service import GraphRepository
from backend.services.node_service import find_node_detail

router = APIRouter(tags=["graph"])

Repo = Annotated[GraphRepository, Depends(get_repo)]
Scenarios = Annotated[dict[str, Scenario], Depends(get_scenarios)]


@router.get("/scenarios", response_model=list[ScenarioSummary])
def list_scenarios(scenarios: Scenarios) -> list[ScenarioSummary]:
    return [_summary(s) for s in scenarios.values()]


@router.get("/graph/scenario/{scenario_id}", response_model=ScenarioGraph)
def scenario_graph(scenario_id: str, repo: Repo, scenarios: Scenarios) -> ScenarioGraph:
    graph = repo.get_graph(scenario_id)
    if scenario_id not in scenarios or graph is None:
        raise HTTPException(status_code=404, detail=f"scenario not found or not seeded: {scenario_id}")
    return ScenarioGraph(scenario=_summary(scenarios[scenario_id]), nodes=graph.nodes, edges=graph.edges)


@router.get("/node/{node_id}", response_model=NodeDetail)
def node_detail(node_id: str, repo: Repo, scenario: str | None = None) -> NodeDetail:
    detail = find_node_detail(repo, node_id, scenario)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"node not found: {node_id}")
    return detail


@router.get("/ontology")
def ontology() -> dict:
    return {
        "node_types": {k.value: v for k, v in NODE_DESCRIPTIONS.items()},
        "edge_types": {k.value: v for k, v in EDGE_DESCRIPTIONS.items()},
    }


def _summary(scenario: Scenario) -> ScenarioSummary:
    return ScenarioSummary(**scenario.model_dump(exclude={"graph"}))
