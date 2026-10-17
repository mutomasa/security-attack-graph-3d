"""Wire concrete implementations together based on configuration."""

from backend.config import LLMSettings, graph_backend, llm_settings, neo4j_settings
from backend.services.graph_service import GraphRepository, InMemoryGraphRepository, Neo4jGraphRepository
from backend.services.intent_service import FallbackIntentParser, LLMIntentParser, RuleBasedIntentParser
from backend.services.llm_service import OpenAICompatibleClient
from backend.services.query_service import QueryService
from backend.services.seed_loader import load_all_scenarios
from backend.services.seeder import seed_repository
from backend.services.summary_service import GuidedLLMSummarizer, LLMSummarizer, SafeSummarizer


def build_repository(backend: str | None = None) -> GraphRepository:
    if (backend or graph_backend()) == "memory":
        repo = InMemoryGraphRepository()
        seed_repository(repo)
        return repo
    return Neo4jGraphRepository.from_settings(neo4j_settings())


def build_query_service(repo: GraphRepository, settings: LLMSettings | None = None) -> QueryService:
    settings = settings or llm_settings()
    llm = OpenAICompatibleClient(settings) if settings.enabled else None
    return QueryService(
        scenarios=load_all_scenarios(),
        repo=repo,
        intent_parser=FallbackIntentParser(_intent_parser(llm, settings), RuleBasedIntentParser()),
        explainer=_explainer(llm, settings),
    )


def _intent_parser(llm, settings: LLMSettings) -> LLMIntentParser | None:
    return LLMIntentParser(llm, guided=settings.guided) if llm else None


def _explainer(llm, settings: LLMSettings) -> SafeSummarizer | None:
    if not llm:
        return None
    return SafeSummarizer(GuidedLLMSummarizer(llm) if settings.guided else LLMSummarizer(llm))
