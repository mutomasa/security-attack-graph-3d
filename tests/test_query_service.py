import pytest

from backend.config import LLMSettings
from backend.models.schemas import IntentType, QueryOptions
from backend.services.factory import build_query_service, build_repository
from backend.services.query_service import UnknownScenarioError

OFFLINE = LLMSettings(enabled=False, base_url="", model="", timeout=1)


@pytest.fixture(scope="module")
def service():
    return build_query_service(build_repository("memory"), OFFLINE)


def test_highest_risk_query_returns_paths_cypher_and_summary(service):
    result = service.run("顧客データに到達する最も危険な経路は？", "demo_company_a")
    assert result.intent.intent == IntentType.HIGHEST_RISK_PATH
    assert len(result.paths) == 3
    assert result.paths[0].score >= result.paths[1].score
    assert 'label = "Internet"' in result.cypher
    assert result.summary.startswith("最も危険な経路")


def test_list_query_returns_more_paths(service):
    result = service.run("Internet から侵入可能な経路だけ表示して", "demo_company_a")
    assert len(result.paths) == 6


def test_required_permissions_lists_identity_permissions(service):
    result = service.run("S3 Bucket に到達するまでに必要な権限は？", "demo_company_a")
    assert [p.label for p in result.permissions] == ["s3:GetObject"]


def test_blast_radius_lists_reached_nodes(service):
    result = service.run("Service Account が漏洩した場合の影響範囲は？", "demo_company_a")
    assert {n.label for n in result.reached} == {"S3 Bucket", "Customer Data"}
    assert "any(l IN labels(target)" in result.cypher


def test_options_override_depth_and_threshold(service):
    result = service.run("顧客データに到達する最も危険な経路は？", "demo_company_a",
                         QueryOptions(top_n=10, max_depth=5, min_score=12))
    assert result.paths and all(p.score >= 12 and len(p.edges) <= 5 for p in result.paths)


def test_no_path_gives_explanation(service):
    result = service.run("顧客データに到達する最も危険な経路は？", "demo_company_a", QueryOptions(max_depth=1))
    assert result.paths == []
    assert "見つかりませんでした" in result.summary


def test_unknown_scenario(service):
    with pytest.raises(UnknownScenarioError):
        service.run("q", "nope")


class FakeLLM:
    def __init__(self, replies):
        self.replies = list(replies)

    def complete(self, prompt, *, json_mode=False, max_tokens=256):
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def _service_with(llm):
    from backend.services.intent_service import FallbackIntentParser, LLMIntentParser, RuleBasedIntentParser
    from backend.services.query_service import QueryService
    from backend.services.seed_loader import load_all_scenarios
    from backend.services.summary_service import LLMSummarizer, SafeSummarizer

    return QueryService(
        load_all_scenarios(), build_repository("memory"),
        FallbackIntentParser(LLMIntentParser(llm), RuleBasedIntentParser()), SafeSummarizer(LLMSummarizer(llm)),
    )


def test_llm_explanation_is_separate_from_template_summary():
    llm = FakeLLM(['{"intent": "find_highest_risk_path", "source": "Internet", "target": "Customer Data"}', "AI解説"])
    result = _service_with(llm).run("顧客データに到達する最も危険な経路は？", "demo_company_a")
    assert result.explanation == "AI解説"
    assert result.summary.startswith("最も危険な経路")


def test_llm_outage_still_answers():
    from backend.services.llm_service import LLMError

    result = _service_with(FakeLLM([LLMError("down"), LLMError("down")])).run(
        "顧客データに到達する最も危険な経路は？", "demo_company_a")
    assert result.paths and result.explanation is None and result.intent.parsed_by == "rule"
