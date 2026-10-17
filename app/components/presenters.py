"""Pure formatting helpers for the Streamlit panels (kept free of Streamlit for unit tests)."""

from backend.models.schemas import AttackPath, Node, NodeDetail

EXAMPLE_QUESTIONS = [
    "顧客データに到達する最も危険な経路は？",
    "Internet から侵入可能な経路だけ表示して",
    "CVE-XXXX を起点にどの資産へ横展開できる？",
    "S3 Bucket に到達するまでに必要な権限は？",
    "Service Account が漏洩した場合の影響範囲は？",
]

INTENT_LABELS = {
    "find_highest_risk_path": "最も危険な経路",
    "list_attack_paths": "攻撃経路の一覧",
    "blast_radius": "影響範囲（横展開）",
    "required_permissions": "到達に必要な権限",
}


def path_text(path: AttackPath) -> str:
    return " → ".join(n.label for n in path.nodes)


def path_rows(paths: list[AttackPath]) -> list[dict]:
    return [
        {"rank": i + 1, "score": p.score, "hops": len(p.edges), "path": path_text(p)}
        for i, p in enumerate(paths)
    ]


def breakdown_rows(path: AttackPath) -> list[dict]:
    return [{"factor": k, "value": v} for k, v in path.score_breakdown.items()]


def node_attribute_rows(node: Node) -> list[dict]:
    rows = [{"attribute": "type", "value": node.type.value}, {"attribute": "id", "value": node.id}]
    rows += [{"attribute": k, "value": str(v)} for k, v in (node.model_extra or {}).items()]
    return rows


def relation_rows(detail: NodeDetail) -> list[dict]:
    labels = {n.id: n.label for n in detail.neighbors} | {detail.node.id: detail.node.label}
    out = [{"direction": "→", "edge": e.type.value, "node": labels[e.target]} for e in detail.outgoing]
    inc = [{"direction": "←", "edge": e.type.value, "node": labels[e.source]} for e in detail.incoming]
    return out + inc


def node_options(nodes: list[Node], preferred: list[Node] | None = None) -> list[tuple[str, str]]:
    """(id, display) pairs; nodes on the highlighted path come first."""
    first = {n.id for n in preferred or []}
    ordered = [n for n in preferred or []] + [n for n in nodes if n.id not in first]
    return [(n.id, f"{n.label} ({n.type.value})") for n in ordered]
