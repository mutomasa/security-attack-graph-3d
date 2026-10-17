"""Evaluate the configured LLM on the demo questions (issue #7).

Usage: VLLM_MODEL=... VLLM_BASE_URL=... uv run python scripts/eval_llm.py

Reports, per question: intent/source/target correctness, latency, and for the LLM explanation
how many path labels it mentions and which labels from *outside* the path it brings in.
"""

import time
from dataclasses import dataclass

from backend.config import llm_settings
from backend.models.schemas import QueryResult, Scenario
from backend.services.factory import build_query_service, build_repository
from backend.services.seed_loader import load_all_scenarios


@dataclass(frozen=True)
class Case:
    scenario: str
    question: str
    intent: str
    source: str
    target: str | None


CASES = [
    Case("demo_company_a", "顧客データに到達する最も危険な経路は？", "find_highest_risk_path", "Internet", "Customer Data"),
    Case("demo_company_a", "Internet から侵入可能な経路だけ表示して", "list_attack_paths", "Internet", "Customer Data"),
    Case("demo_company_a", "CVE-XXXX を起点にどの資産へ横展開できる？", "blast_radius", "CVE-XXXX", None),
    Case("demo_company_a", "S3 Bucket に到達するまでに必要な権限は？", "required_permissions", "Internet", "S3 Bucket"),
    Case("demo_company_a", "Service Account が漏洩した場合の影響範囲は？", "blast_radius", "Service Account", None),
    Case("demo_company_b", "API Key が漏れたら顧客データまで届く？", "find_highest_risk_path", "CI Deploy API Key",
         "Customer Data"),
    Case("demo_company_c", "機密テーブルに到達する最も危険な経路は？", "find_highest_risk_path", "Internal User",
         "Sensitive Table"),
]


def intent_ok(case: Case, result: QueryResult) -> bool:
    got = result.intent
    return (got.intent.value, got.source, got.target) == (case.intent, case.source, case.target)


def explanation_labels(result: QueryResult, scenario: Scenario) -> tuple[int, int, list[str]]:
    """(path labels mentioned, path length, scenario labels mentioned that are not on the path)."""
    text = result.explanation or ""
    on_path = {n.label for n in result.paths[0].nodes} if result.paths else set()
    foreign = sorted(
        n.label
        for n in scenario.graph.nodes
        if n.label not in on_path and n.label in text and not any(n.label in p for p in on_path)
    )
    return sum(label in text for label in on_path), len(on_path), foreign


def main() -> None:
    settings = llm_settings()
    scenarios = load_all_scenarios()
    service = build_query_service(build_repository("memory"), settings)
    print(f"model: {settings.model} @ {settings.base_url}\n")
    correct = 0
    for case in CASES:
        start = time.perf_counter()
        result = service.run(case.question, case.scenario)
        elapsed = time.perf_counter() - start
        ok = intent_ok(case, result)
        correct += ok
        hit, total, foreign = explanation_labels(result, scenarios[case.scenario])
        print(f"[{'OK' if ok else 'NG'}] {elapsed:4.1f}s {case.question}")
        print(f"     intent={result.intent.intent.value} {result.intent.source} -> {result.intent.target}"
              f" ({result.intent.parsed_by})")
        print(f"     explanation: path labels {hit}/{total}, foreign labels {foreign or '-'}")
        print(f"     {(result.explanation or '(none)').replace(chr(10), ' ')}\n")
    print(f"intent accuracy: {correct}/{len(CASES)}")


if __name__ == "__main__":
    main()
