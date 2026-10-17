"""Security Attack Graph 3D — Streamlit UI.  Run: uv run streamlit run app/streamlit_app.py"""

import streamlit as st

from app import api_client
from app.components.graph_view import render_graph
from app.components.node_detail import render_node_detail
from app.components.presenters import EXAMPLE_QUESTIONS
from app.components.summary_panel import render_path_list, render_summary
from backend.models.ontology import MAX_PATH_DEPTH
from backend.models.schemas import Graph, QueryRequest, QueryResponse, ScenarioSummary


@st.cache_resource
def get_client() -> api_client.ApiClient:
    return api_client.build_client()


def ask(question: str) -> None:
    st.session_state.question = question
    st.session_state.run_requested = True


def sidebar(scenarios: list[ScenarioSummary]) -> tuple[ScenarioSummary, dict]:
    with st.sidebar:
        st.header("Scenario")
        by_id = {s.id: s for s in scenarios}
        scenario_id = st.selectbox("シナリオ選択", list(by_id), format_func=lambda i: by_id[i].name)
        st.caption(by_id[scenario_id].description)
        st.header("クエリ例")
        for i, q in enumerate(EXAMPLE_QUESTIONS):
            st.button(q, key=f"example_{i}", on_click=ask, args=(q,), width="stretch")
        st.header("Filters")
        options = {
            "min_score": st.slider("リスクしきい値（最小スコア）", 0.0, 25.0, 0.0, 0.5),
            "max_depth": st.slider("最大深さ", 1, MAX_PATH_DEPTH, 8),
            "top_n": st.slider("表示する経路数 (Top N)", 1, 10, 3),
        }
        if st.button("ダミーデータを再投入 (POST /seed)", width="stretch"):
            get_client().seed()
            st.cache_data.clear()
            st.toast("Seed 完了")
    return by_id[scenario_id], options


def run_query(scenario: ScenarioSummary, options: dict) -> None:
    question = st.session_state.get("question", "").strip()
    if not question:
        st.warning("質問を入力してください")
        return
    with st.spinner("Attack Path を探索中..."):
        try:
            result = get_client().query(QueryRequest(question=question, scenario=scenario.id, **options))
        except api_client.BackendError as exc:
            st.error(str(exc))
            return
    st.session_state.result = {"scenario": scenario.id, "response": result}


def current_result(scenario_id: str) -> QueryResponse | None:
    stored = st.session_state.get("result")
    return stored["response"] if stored and stored["scenario"] == scenario_id else None


def main() -> None:
    st.set_page_config(page_title="Security Attack Graph 3D", page_icon="🛡️", layout="wide")
    st.title("🛡️ Security Attack Graph 3D")
    st.caption("脆弱性を「点」ではなく「経路」で捉える — どこから侵入し、どの権限を奪い、どのデータへ到達するか")

    client = get_client()
    try:
        scenarios = client.scenarios()
    except api_client.BackendError as exc:
        st.error(f"バックエンドに接続できません: {exc}")
        st.stop()
    scenario, options = sidebar(scenarios)

    st.text_input("質問", key="question", placeholder=EXAMPLE_QUESTIONS[0])
    if st.button("実行", type="primary") or st.session_state.pop("run_requested", False):
        run_query(scenario, options)

    try:
        scenario_graph = client.scenario_graph(scenario.id)
    except api_client.BackendError:
        st.warning("シナリオが未投入です。サイドバーの「ダミーデータを再投入」を押してください。")
        st.stop()
    graph = Graph(nodes=scenario_graph.nodes, edges=scenario_graph.edges)
    result = current_result(scenario.id)
    paths = result.paths if result else []

    render_graph(graph, paths, entry=result.intent_detail.source if result else scenario.default_source)
    if result:
        render_summary(result)
        if result.paths:
            render_path_list(result)
        with st.expander("Cypher（デバッグ用）"):
            st.code(result.cypher, language="cypher")
    render_node_detail(client, scenario.id, graph.nodes, paths[0].nodes if paths else [])


main()
