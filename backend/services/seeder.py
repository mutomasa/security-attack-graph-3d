"""Load bundled seed scenarios into a graph repository."""

from pathlib import Path

from backend.services.graph_service import GraphRepository
from backend.services.seed_loader import DEFAULT_SEED_DIR, load_all_scenarios


def seed_repository(repo: GraphRepository, seed_dir: Path = DEFAULT_SEED_DIR) -> list[str]:
    scenarios = load_all_scenarios(seed_dir)
    for scenario in scenarios.values():
        repo.save_scenario(scenario)
    return sorted(scenarios)
