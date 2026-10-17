import streamlit as st

from app.api_client import ApiClient, BackendError
from app.components.presenters import node_attribute_rows, node_options, relation_rows
from backend.models.schemas import Node


def render_node_detail(client: ApiClient, scenario_id: str, nodes: list[Node], preferred: list[Node]) -> None:
    st.subheader("Detail Panel")
    options = node_options(nodes, preferred)
    labels = dict(options)
    node_id = st.selectbox("ノードを選択", [o[0] for o in options], format_func=labels.get, key="detail_node")
    if not node_id:
        return
    try:
        detail = client.node(node_id, scenario_id)
    except BackendError as exc:
        st.error(str(exc))
        return
    left, right = st.columns(2)
    left.dataframe(node_attribute_rows(detail.node), hide_index=True, width="stretch")
    right.dataframe(relation_rows(detail), hide_index=True, width="stretch")
