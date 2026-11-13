"""Configuration from environment. No credentials are bundled in this project."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
ROOT = Path(__file__).resolve().parents[2]


def _int(name: str, default: int, minimum: int = 1) -> int:
    value = int(os.getenv(name, default))
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


@dataclass(frozen=True)
class Settings:
    database_url: str
    github_token: str | None
    max_repos: int
    max_candidates: int
    max_pages: int
    search_pages: int
    per_page: int
    freshness_days: int
    backfill_days: int
    comparison_days: int
    overlap_hours: int
    max_retries: int
    timeout_seconds: int
    stale_hours: int

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=os.getenv("DATABASE_URL") or f"sqlite:///{ROOT / 'local.sqlite3'}",
            github_token=os.getenv("GITHUB_TOKEN") or None,
            max_repos=_int("MAX_REPOS", 50),
            max_candidates=_int("MAX_CANDIDATES", 320),
            max_pages=_int("MAX_PAGES_PER_SOURCE", 6),
            search_pages=_int("SEARCH_PAGES_PER_QUERY", 2),
            per_page=_int("PER_PAGE", 100),
            freshness_days=_int("FRESHNESS_DAYS", 30),
            backfill_days=_int("BACKFILL_DAYS", 180),
            comparison_days=_int("COMPARISON_DAYS", 90),
            overlap_hours=_int("OVERLAP_HOURS", 48),
            max_retries=_int("MAX_RETRIES", 4),
            timeout_seconds=_int("TIMEOUT_SECONDS", 20),
            stale_hours=_int("STALE_HOURS", 12),
        )

    def cutoff(self, days: int | None = None) -> datetime:
        return datetime.now(timezone.utc) - timedelta(days=days or self.backfill_days)


LANGUAGE_GROUPS = {
    "Python": "Data & backend", "JavaScript": "Web applications",
    "TypeScript": "Web applications", "Go": "Cloud & infrastructure",
    "Rust": "Systems & tooling", "Java": "Enterprise applications",
    "C#": "Enterprise applications", "Ruby": "Web applications",
    "C++": "Systems & tooling", "Kotlin": "Mobile applications",
    "Swift": "Mobile applications", "Dart": "Mobile applications",
    "PHP": "Web applications", "C": "Systems & tooling",
}

SEARCH_QUERIES = (
    "language:Python", "language:TypeScript", "language:Go",
    "language:Rust", "language:Java", "language:Kotlin",
    "language:C++", "language:Ruby", "language:Swift",
    "language:PHP", "language:C#", "language:JavaScript",
    "language:Dart", "language:C",
)
