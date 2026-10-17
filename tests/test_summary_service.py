import pytest

from backend.models.schemas import AttackPath
from backend.services.llm_service import LLMError
from backend.services.summary_service import (
    LLMSummarizer,
    SafeSummarizer,
    TemplateSummarizer,
    format_path,
    label_coverage,
)

PATH = AttackPath(
    score=16.19,
    nodes=[
        {"id": "i", "label": "Internet", "type": "NetworkZone"},
        {"id": "w", "label": "Web Server", "type": "Asset"},
        {"id": "c", "label": "CVE-XXXX", "type": "Vulnerability"},
        {"id": "s", "label": "Credential Leak", "type": "Secret"},
        {"id": "a", "label": "Service Account", "type": "Identity"},
        {"id": "b", "label": "S3 Bucket", "type": "Asset"},
        {"id": "d", "label": "Customer Data", "type": "Data"},
    ],
    edges=[
        {"source": "i", "target": "w", "type": "EXPOSED_TO"},
        {"source": "w", "target": "c", "type": "HAS_VULNERABILITY"},
        {"source": "c", "target": "s", "type": "LEADS_TO"},
        {"source": "s", "target": "a", "type": "LEADS_TO"},
        {"source": "a", "target": "b", "type": "CAN_ACCESS"},
        {"source": "b", "target": "d", "type": "STORES"},
    ],
)


class FakeLLM:
    def __init__(self, reply):
        self.reply = reply
        self.prompt = ""

    def complete(self, prompt, **kwargs):
        self.prompt = prompt
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


def test_template_summary_mentions_every_step_in_order():
    text = TemplateSummarizer().summarize("q", PATH)
    positions = [text.index(n.label) for n in PATH.nodes]
    assert positions == sorted(positions)
    assert text.startswith("最も危険な経路（スコア 16.19）は、Internet から公開された Web Server")
    assert text.endswith("Customer Data に到達する経路です。")


def test_template_summary_adds_start_when_first_step_omits_it():
    sub = AttackPath(score=1, nodes=PATH.nodes[3:], edges=PATH.edges[3:])
    assert "Credential Leak を起点に" in TemplateSummarizer().summarize("q", sub)


def test_llm_summary_with_translated_labels_is_rejected():
    translated = "インターネットからウェブサーバーの脆弱性を突き、顧客データに到達します。"
    with pytest.raises(LLMError, match="path labels"):
        LLMSummarizer(FakeLLM(translated)).summarize("q", PATH)
    assert SafeSummarizer(LLMSummarizer(FakeLLM(translated))).summarize("q", PATH) is None


def test_label_coverage():
    assert label_coverage(GOOD, PATH) == 6 / 7
    assert label_coverage("", PATH) == 0


def test_template_summary_without_path():
    assert "見つかりませんでした" in TemplateSummarizer().summarize("q", None)


GOOD = "Internet から Web Server の CVE-XXXX を突き、Credential Leak で Service Account を奪い S3 Bucket に到達。"


def test_llm_summary_receives_structured_path():
    llm = FakeLLM(f" {GOOD} ")
    assert LLMSummarizer(llm).summarize("顧客データは？", PATH) == GOOD
    assert format_path(PATH) in llm.prompt
    assert "顧客データは？" in llm.prompt


def test_safe_summarizer_returns_none_on_llm_error():
    assert SafeSummarizer(LLMSummarizer(FakeLLM(LLMError("down")))).summarize("q", PATH) is None
