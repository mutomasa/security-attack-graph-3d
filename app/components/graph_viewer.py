"""Render the Three.js attack graph as a self-contained HTML document."""

import json
from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parents[1] / "static" / "threejs"


def render_graph_html(view_model: dict, height: int = 640) -> str:
    template = (STATIC_DIR / "graph_viewer.html").read_text(encoding="utf-8")
    script = (STATIC_DIR / "graph_viewer.js").read_text(encoding="utf-8")
    return (
        template.replace("__HEIGHT__", str(height))
        .replace("__GRAPH_DATA__", _safe_json(view_model))
        .replace("__VIEWER_SCRIPT__", script)
    )


def _safe_json(data: dict) -> str:
    """JSON that cannot terminate the surrounding <script> element."""
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
