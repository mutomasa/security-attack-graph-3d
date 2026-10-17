"""Build read-only attack-path Cypher from a structured PathQuery.

Only enum-backed identifiers (edge types, node types) and a bounded integer depth are
interpolated; all user-provided values are passed as parameters.
"""

from dataclasses import dataclass

from backend.models.schemas import PathQuery

_RETURN_CLAUSE = (
    "RETURN [n IN nodes(p) | properties(n)] AS nodes,\n"
    "       [r IN relationships(p) | {source: startNode(r).id, target: endNode(r).id,"
    " type: type(r), weight: r.weight}] AS edges\n"
    "LIMIT $limit"
)


@dataclass(frozen=True)
class CypherQuery:
    text: str
    params: dict

    def display(self) -> str:
        """Human-readable Cypher with parameters inlined (for the debug panel only)."""
        text = self.text
        for key in sorted(self.params, key=len, reverse=True):
            text = text.replace(f"${key}", _literal(self.params[key]))
        return text


def build_path_query(query: PathQuery) -> CypherQuery:
    text = "\n".join([_match_clause(query), _where_clause(query), _RETURN_CLAUSE])
    return CypherQuery(text=text, params=_params(query))


def _match_clause(query: PathQuery) -> str:
    rel_types = "|".join(t.value for t in query.edge_types)
    return (
        "MATCH p = (start {scenario: $scenario})\n"
        f"  -[:{rel_types}*1..{int(query.max_depth)}]->\n"
        "  (target {scenario: $scenario})"
    )


def _where_clause(query: PathQuery) -> str:
    conditions = [
        "(start.label = $source OR start.id = $source)",
        _target_condition(query),
        # Cypher only guarantees relationship uniqueness; drop paths that revisit a node.
        "all(n IN nodes(p) WHERE single(m IN nodes(p) WHERE m = n))",
    ]
    return "WHERE " + "\n  AND ".join(conditions)


def _target_condition(query: PathQuery) -> str:
    if query.target:
        return "(target.label = $target OR target.id = $target)"
    return "any(l IN labels(target) WHERE l IN $target_types)"


def _params(query: PathQuery) -> dict:
    params = {"scenario": query.scenario_id, "source": query.source, "limit": query.candidate_limit}
    if query.target:
        params["target"] = query.target
    else:
        params["target_types"] = [t.value for t in query.target_types]
    return params


def _literal(value) -> str:
    if isinstance(value, str):
        return '"' + value.replace('"', '\\"') + '"'
    if isinstance(value, list):
        return "[" + ", ".join(_literal(v) for v in value) + "]"
    return str(value)
