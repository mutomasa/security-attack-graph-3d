"""Load scenario seed files (YAML) into validated Scenario models."""

from pathlib import Path

import yaml

from backend.models.schemas import Graph, Scenario

DEFAULT_SEED_DIR = Path(__file__).resolve().parents[2] / "data" / "seed"


def load_scenario(path: Path) -> Scenario:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return _to_scenario(raw)


def load_all_scenarios(seed_dir: Path = DEFAULT_SEED_DIR) -> dict[str, Scenario]:
    scenarios = [load_scenario(p) for p in sorted(seed_dir.glob("*.yaml"))]
    return {s.id: s for s in scenarios}


def _to_scenario(raw: dict) -> Scenario:
    meta = raw["scenario"]
    graph = Graph(nodes=raw.get("nodes", []), edges=raw.get("edges", []))
    return Scenario(graph=graph, **meta)
