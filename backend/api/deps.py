"""FastAPI dependencies: services are created once in the app lifespan and stored on app.state."""

from fastapi import Request

from backend.models.schemas import Scenario
from backend.services.graph_service import GraphRepository
from backend.services.query_service import QueryService


def get_repo(request: Request) -> GraphRepository:
    return request.app.state.repo


def get_query_service(request: Request) -> QueryService:
    return request.app.state.query_service


def get_scenarios(request: Request) -> dict[str, Scenario]:
    return request.app.state.scenarios
