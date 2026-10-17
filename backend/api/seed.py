from typing import Annotated

from fastapi import APIRouter, Depends

from backend.api.deps import get_repo
from backend.services.graph_service import GraphRepository
from backend.services.seeder import seed_repository

router = APIRouter(tags=["seed"])


@router.post("/seed")
def seed(repo: Annotated[GraphRepository, Depends(get_repo)]) -> dict:
    return {"seeded": seed_repository(repo)}
