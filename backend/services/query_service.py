"""Orchestrates a natural-language query: intent -> PathQuery -> ranked paths -> explanation."""

from backend.models.ontology import EdgeType, NodeType
from backend.models.schemas import (
    AttackPath,
    Intent,
    IntentType,
    Node,
    PathQuery,
    QueryOptions,
    QueryResult,
    Scenario,
)
from backend.services.cypher_builder import build_path_query
from backend.services.graph_service import GraphRepository
from backend.services.intent_service import IntentParser
from backend.services.path_service import AttackPathService
from backend.services.summary_service import Summarizer, TemplateSummarizer

BLAST_RADIUS_TYPES = [NodeType.ASSET, NodeType.DATA, NodeType.IDENTITY, NodeType.SECRET]
LIST_TOP_N = 10
BLAST_TOP_N = 50


class UnknownScenarioError(KeyError):
    pass


class QueryService:
    def __init__(
        self,
        scenarios: dict[str, Scenario],
        repo: GraphRepository,
        intent_parser: IntentParser,
        explainer: Summarizer | None = None,
    ) -> None:
        self._scenarios = scenarios
        self._repo = repo
        self._paths = AttackPathService(repo)
        self._intent_parser = intent_parser
        self._summarizer = TemplateSummarizer()
        self._explainer = explainer

    def run(self, question: str, scenario_id: str, options: QueryOptions | None = None) -> QueryResult:
        options = options or QueryOptions()
        scenario = self._scenario(scenario_id)
        intent = self._intent_parser.parse(question, scenario)
        path_query = to_path_query(intent, scenario_id, options)
        paths = self._paths.find_top_paths(path_query)
        top = paths[0] if paths else None
        return QueryResult(
            intent=intent,
            cypher=build_path_query(path_query).display(),
            paths=paths,
            summary=self._summarizer.summarize(question, top),
            explanation=self._explain(question, top),
            permissions=self._permissions(intent, scenario_id, paths),
            reached=reached_nodes(paths) if intent.intent == IntentType.BLAST_RADIUS else [],
        )

    def _scenario(self, scenario_id: str) -> Scenario:
        try:
            return self._scenarios[scenario_id]
        except KeyError as exc:
            raise UnknownScenarioError(scenario_id) from exc

    def _explain(self, question: str, top: AttackPath | None) -> str | None:
        if not self._explainer or top is None:
            return None
        return self._explainer.summarize(question, top)

    def _permissions(self, intent: Intent, scenario_id: str, paths: list[AttackPath]) -> list[Node]:
        if intent.intent != IntentType.REQUIRED_PERMISSIONS or not paths:
            return []
        graph = self._repo.get_graph(scenario_id)
        return permissions_on_path(paths[0], graph.edges, graph.node_by_id()) if graph else []


def to_path_query(intent: Intent, scenario_id: str, options: QueryOptions) -> PathQuery:
    common = {
        "scenario_id": scenario_id,
        "source": intent.source,
        "edge_types": intent.path_types,
        "max_depth": options.max_depth or intent.max_depth,
        "min_score": options.min_score,
    }
    if intent.intent == IntentType.BLAST_RADIUS:
        return PathQuery(**common, target=None, target_types=BLAST_RADIUS_TYPES, top_n=BLAST_TOP_N)
    top_n = max(options.top_n, LIST_TOP_N) if intent.intent == IntentType.LIST_ATTACK_PATHS else options.top_n
    return PathQuery(**common, target=intent.target, top_n=top_n)


def permissions_on_path(path: AttackPath, edges, nodes: dict[str, Node]) -> list[Node]:
    identity_ids = {n.id for n in path.nodes if n.type == NodeType.IDENTITY}
    perm_ids = [e.target for e in edges if e.type == EdgeType.HAS_PERMISSION and e.source in identity_ids]
    return [nodes[i] for i in dict.fromkeys(perm_ids)]


def reached_nodes(paths: list[AttackPath]) -> list[Node]:
    seen: dict[str, Node] = {}
    for path in paths:
        seen.setdefault(path.nodes[-1].id, path.nodes[-1])
    return list(seen.values())
