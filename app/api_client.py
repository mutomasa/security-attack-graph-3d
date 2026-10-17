"""Thin HTTP client for the FastAPI backend."""

import os

import httpx

from backend.models.schemas import NodeDetail, QueryRequest, QueryResponse, ScenarioGraph, ScenarioSummary


class BackendError(RuntimeError):
    pass


class ApiClient:
    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def scenarios(self) -> list[ScenarioSummary]:
        return [ScenarioSummary(**s) for s in self._get("/scenarios")]

    def scenario_graph(self, scenario_id: str) -> ScenarioGraph:
        return ScenarioGraph(**self._get(f"/graph/scenario/{scenario_id}"))

    def node(self, node_id: str, scenario_id: str) -> NodeDetail:
        return NodeDetail(**self._get(f"/node/{node_id}", params={"scenario": scenario_id}))

    def query(self, request: QueryRequest) -> QueryResponse:
        return QueryResponse(**self._send("POST", "/query", json=request.model_dump()))

    def seed(self) -> list[str]:
        return self._send("POST", "/seed")["seeded"]

    def _get(self, path: str, params: dict | None = None):
        return self._send("GET", path, params=params)

    def _send(self, method: str, path: str, **kwargs):
        try:
            response = self._http.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            raise BackendError(f"{exc.response.status_code}: {exc.response.text}") from exc
        except httpx.HTTPError as exc:
            raise BackendError(f"backend unreachable: {exc}") from exc


def build_client() -> ApiClient:
    base_url = os.environ.get("BACKEND_URL", "http://localhost:8010")
    return ApiClient(httpx.Client(base_url=base_url, timeout=60))
