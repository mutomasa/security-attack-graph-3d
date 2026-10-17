from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from app import api_client
from backend.config import LLMSettings
from backend.main import create_app
from backend.services.factory import build_query_service
from backend.services.graph_service import InMemoryGraphRepository
from backend.services.seeder import seed_repository

OFFLINE = LLMSettings(enabled=False, base_url="", model="", timeout=1)
APP = str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py")


@pytest.fixture
def backend(monkeypatch):
    repo = InMemoryGraphRepository()
    seed_repository(repo)
    with TestClient(create_app(repo=repo, query_service=build_query_service(repo, OFFLINE))) as http:
        monkeypatch.setattr(api_client, "build_client", lambda: api_client.ApiClient(http))
        yield repo


@pytest.fixture(autouse=True)
def _clear_streamlit_cache():
    import streamlit as st

    st.cache_resource.clear()
    yield
    st.cache_resource.clear()


def _run(target) -> AppTest:
    """Run an AppTest, or the AppTest behind a widget interaction (click/select return the widget)."""
    at = target.run(timeout=30)
    assert not at.exception, at.exception
    return at


def test_initial_render_shows_scenario_graph(backend):
    at = _run(AppTest.from_file(APP))
    assert at.title[0].value.endswith("Security Attack Graph 3D")
    assert at.sidebar.selectbox[0].value == "demo_company_a"
    assert len(at.get("iframe")) == 1
    assert at.selectbox(key="detail_node").value is not None


def test_query_renders_summary_paths_and_cypher(backend):
    at = _run(AppTest.from_file(APP))
    at.text_input(key="question").set_value("顧客データに到達する最も危険な経路は？")
    _run(next(b for b in at.button if b.label == "実行").click())
    assert any("Top Risk Path" in e.value for e in at.error)
    assert at.metric[0].value == "16.19"
    assert any("MATCH p =" in c.value for c in at.code)


def test_example_button_runs_query(backend):
    at = _run(AppTest.from_file(APP))
    _run(at.button(key="example_3").click())
    assert any("s3:GetObject" in i.value for i in at.info)


def test_switching_scenario_resets_result(backend):
    at = _run(AppTest.from_file(APP))
    _run(at.button(key="example_0").click())
    assert at.metric
    _run(at.sidebar.selectbox[0].select("demo_company_c"))
    assert not at.metric


def test_backend_down_shows_error(monkeypatch):
    import httpx

    def refuse(request):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(api_client, "build_client",
                        lambda: api_client.ApiClient(httpx.Client(base_url="http://x", transport=httpx.MockTransport(refuse))))
    at = AppTest.from_file(APP)
    at.run(timeout=30)
    assert any("バックエンドに接続できません" in e.value for e in at.error)
