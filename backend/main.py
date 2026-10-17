"""FastAPI entrypoint.  Run: uv run uvicorn backend.main:app --port 8010"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.api import graph, query, seed
from backend.services.factory import build_query_service, build_repository
from backend.services.graph_service import GraphRepository
from backend.services.query_service import QueryService
from backend.services.seed_loader import load_all_scenarios


def create_app(repo: GraphRepository | None = None, query_service: QueryService | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.repo = repo or build_repository()
        app.state.scenarios = load_all_scenarios()
        app.state.query_service = query_service or build_query_service(app.state.repo)
        yield
        close = getattr(app.state.repo, "close", None)
        if close and repo is None:
            close()

    app = FastAPI(title="Security Attack Graph 3D", version="0.1.0", lifespan=lifespan)
    for module in (query, graph, seed):
        app.include_router(module.router)
    app.get("/health")(lambda: {"status": "ok"})
    return app


app = create_app()
