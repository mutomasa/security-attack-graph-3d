from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from backend.api.deps import get_query_service
from backend.models.schemas import QueryRequest, QueryResponse
from backend.services.query_service import QueryService, UnknownScenarioError

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
def query(req: QueryRequest, service: Annotated[QueryService, Depends(get_query_service)]) -> QueryResponse:
    try:
        result = service.run(req.question, req.scenario, req.options())
    except UnknownScenarioError as exc:
        raise HTTPException(status_code=404, detail=f"unknown scenario: {req.scenario}") from exc
    return QueryResponse.from_result(result)
