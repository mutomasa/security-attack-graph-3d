import streamlit as st

from app.components.graph_viewer import render_graph_html
from app.components.view_model import build_view_model
from backend.models.schemas import AttackPath, Graph

VIEW_HEIGHT = 620


def render_graph(graph: Graph, paths: list[AttackPath], entry: str | None) -> None:
    html = render_graph_html(build_view_model(graph, paths, entry), height=VIEW_HEIGHT)
    # Content is generated from seed data and escaped JSON, never raw user/LLM HTML.
    st.iframe(html, height=VIEW_HEIGHT + 10)
