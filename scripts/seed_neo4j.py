"""Seed all bundled scenarios into Neo4j.  Usage: uv run python scripts/seed_neo4j.py"""

from backend.config import neo4j_settings
from backend.services.graph_service import Neo4jGraphRepository
from backend.services.seeder import seed_repository


def main() -> None:
    repo = Neo4jGraphRepository.from_settings(neo4j_settings())
    try:
        seeded = seed_repository(repo)
    finally:
        repo.close()
    print(f"seeded scenarios: {', '.join(seeded)}")


if __name__ == "__main__":
    main()
