import streamlit as st

from app.components.presenters import INTENT_LABELS, breakdown_rows, path_rows, path_text
from backend.models.schemas import QueryResponse


def render_summary(result: QueryResponse) -> None:
    st.subheader("Result Summary")
    if not result.paths:
        st.warning(result.summary)
        return
    top = result.paths[0]
    cols = st.columns([1, 1, 1, 3])
    cols[0].metric("Top Risk Score", f"{top.score:.2f}")
    cols[1].metric("Hops", len(top.edges))
    cols[2].metric("Paths", len(result.paths))
    cols[3].metric("Intent", INTENT_LABELS.get(result.intent.value, result.intent.value))
    st.error(f"**Top Risk Path:** {path_text(top)}")
    st.write(result.summary)
    if result.explanation:
        with st.container(border=True):
            st.caption(f"AI 解説（{result.intent_detail.parsed_by} / 小型 LLM のため誤りを含む場合があります）")
            st.write(result.explanation)
    _render_extras(result)


def _render_extras(result: QueryResponse) -> None:
    if result.permissions:
        st.info("到達に必要な権限: " + ", ".join(f"`{p.label}`" for p in result.permissions))
    if result.reached:
        st.info("到達可能なノード: " + ", ".join(f"{n.label} ({n.type.value})" for n in result.reached))


def render_path_list(result: QueryResponse) -> None:
    st.subheader("経路一覧")
    st.dataframe(path_rows(result.paths), hide_index=True, width="stretch")
    with st.expander("Top 1 スコア内訳"):
        st.dataframe(breakdown_rows(result.paths[0]), hide_index=True)
