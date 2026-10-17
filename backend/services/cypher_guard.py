"""Read-only Cypher guardrail (design §10.3, §18.3).

Every Cypher string is checked before it reaches Neo4j. Combined with READ access-mode sessions
this compensates for the missing read-only user on Community Edition (issue #2).
"""

import re

from backend.models.ontology import MAX_PATH_DEPTH, EdgeType, NodeType

WRITE_KEYWORDS = ("CREATE", "MERGE", "DELETE", "DETACH", "SET", "REMOVE", "DROP", "FOREACH", "LOAD", "CALL")
_ALLOWED_LABELS = {t.value for t in NodeType}
_ALLOWED_RELS = {t.value for t in EdgeType}


class UnsafeCypherError(ValueError):
    pass


def validate_read_only_cypher(text: str) -> None:
    stripped = _strip_string_literals(text)
    _reject_multiple_statements(stripped)
    _reject_write_keywords(stripped)
    _reject_unknown_rel_types(stripped)
    _reject_unknown_labels(stripped)
    _reject_deep_traversal(stripped)


def _strip_string_literals(text: str) -> str:
    return re.sub(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"", '""', text)


def _reject_multiple_statements(text: str) -> None:
    if ";" in text.strip().rstrip(";"):
        raise UnsafeCypherError("multiple statements are not allowed")


def _reject_write_keywords(text: str) -> None:
    for keyword in WRITE_KEYWORDS:
        if re.search(rf"\b{keyword}\b", text, re.IGNORECASE):
            raise UnsafeCypherError(f"write/procedure keyword not allowed: {keyword}")


def _reject_unknown_rel_types(text: str) -> None:
    for group in re.findall(r"\[\s*\w*\s*:\s*([^\]*]+)", text):
        for rel in re.split(r"\|:?", group):
            if rel.strip() and rel.strip() not in _ALLOWED_RELS:
                raise UnsafeCypherError(f"relationship type not allowed: {rel.strip()}")


def _reject_unknown_labels(text: str) -> None:
    for label in re.findall(r"\(\s*\w*\s*:\s*`?(\w+)`?", text):
        if label not in _ALLOWED_LABELS:
            raise UnsafeCypherError(f"label not allowed: {label}")


def _reject_deep_traversal(text: str) -> None:
    for lower, dots, upper in re.findall(r"\*\s*(\d*)\s*(\.\.)?\s*(\d*)\s*\]", text):
        depth = upper or (lower if not dots else "")
        if not depth:
            raise UnsafeCypherError("unbounded variable-length path")
        if int(depth) > MAX_PATH_DEPTH:
            raise UnsafeCypherError(f"path depth {depth} exceeds {MAX_PATH_DEPTH}")
