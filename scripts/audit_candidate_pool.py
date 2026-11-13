"""Read-only replacement-candidate scouting with actual 28-day API proofs.

NEVER promote a repository merely because it has stars or recent pushes.
Do not mutate the existing 75-repository selection, database or snapshot.
An independent audit can later support a reviewed substitution decision.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import json
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.analytics.metrics import utc
from src.analytics.snapshot import SNAPSHOT_PATH
from src.collectors.client import GitHubClient, GitHubAPIError
from src.collectors.sync import fetch_source_adaptive
from src.config.settings import Settings
from src.discovery.selection import (
    diversified_sample, validate_candidate, category, size_tier,
)

QUERY_LANGUAGES = ("Python", "TypeScript", "Go", "Java", "Rust",
                   "JavaScript", "Kotlin", "C#")
SOURCES = ("issues", "pull_requests", "workflow_runs")
MIN_ROWS = {"issues": 3, "pull_requests": 3, "workflow_runs": 2}


def discover_candidates(client, known_ids, settings, *, now, max_candidates=24):
    """Discover balanced candidates; keep real GitHub identity and filter."""
    cutoff = (now - timedelta(days=settings.freshness_days)).date().isoformat()
    found = {}
    errors = []
    per_language = max(5, min(15, max_candidates // 4))
    for language in QUERY_LANGUAGES:
        # Sample every configured language, not only the first languages
        # that happened to fill the candidate-search budget.
        q = (
            f"language:{language} is:public fork:false archived:false "
            f"stars:>=50 pushed:>={cutoff}"
        )
        try:
            payload, _ = client.get("/search/repositories", {
                "q": q, "per_page": per_language, "page": 1,
                "sort": "updated", "order": "desc",
            })
        except GitHubAPIError as exc:
            errors.append({"language": language, "reason": type(exc).__name__})
            continue
        if payload.get("incomplete_results"):
            errors.append({"language": language, "reason": "search_results_incomplete"})
        for raw in payload.get("items") or []:
            rid = raw.get("id")
            if not isinstance(rid, int) or rid in known_ids or rid in found:
                continue
            if (reason := validate_candidate(raw, now, settings.freshness_days)):
                continue
            created = utc(raw.get("created_at"))
            if created is None or created > now - timedelta(days=28):
                continue
            found[rid] = raw
    chosen = diversified_sample(list(found.values()), limit=max_candidates)
    return chosen, errors


def probe_candidate(client, raw, settings, *, now):
    """Prove each required REST source period independently; no inferred 75/75."""
    repo = SimpleNamespace(id=int(raw["id"]), full_name=raw["full_name"])
    cutoff = now - timedelta(days=28)
    sources = {}
    complete = True
    for source in SOURCES:
        max_requests = getattr(client, "max_requests", None)
        used = getattr(client, "request_count", 0)
        if max_requests is not None and max_requests - used < settings.max_pages + 8:
            sources[source] = {"status": "budget_exhausted", "records": None}
            complete = False
            break
        try:
            rows, result, effective, attempts, pages = fetch_source_adaptive(
                client, repo, source, cutoff, settings, now,
            )
            verified = bool(result.complete and effective <= cutoff)
            sources[source] = {
                "status": "verified_28d" if verified else "partial_or_short_window",
                "records": len(rows), "pages": pages, "attempts": attempts,
                "source_start_utc": effective.isoformat(),
                "minimum_useful_records": MIN_ROWS[source],
            }
            if not verified or len(rows) < MIN_ROWS[source]:
                complete = False
        except Exception as exc:
            sources[source] = {
                "status": "probe_failed",
                "error_type": type(exc).__name__,
                "records": None,
            }
            complete = False
            break
        if not complete:
            # Never spend large CI request windows on a candidate that
            # already failed the 28-day source verification.
            break
    return {
        "github_id": repo.id, "full_name": repo.full_name,
        "url": raw["html_url"], "category": category(raw),
        "size_tier": size_tier(raw), "language": raw.get("language"),
        "pushed_at": raw.get("pushed_at"),
        "sources": sources,
        "verdict": (
            "verified_candidate" if complete and all(
                sources.get(source, {}).get("status") == "verified_28d"
                and sources[source]["records"] >= MIN_ROWS[source]
                for source in SOURCES
            ) else "not_verified"
        ),
    }


def audit_candidates(client, settings, known_ids, *, now=None,
                     max_candidates=24, max_probes=8):
    now = utc(now or datetime.now(timezone.utc))
    before = getattr(client, "request_count", 0)
    candidates, search_errors = discover_candidates(
        client, known_ids, settings, now=now, max_candidates=max_candidates)
    # Rotate candidate probes on successive UTC calendar days instead of
    # repeatedly spending the same API budget on the first eight projects.
    # The complete candidate pool is disclosed; no unverified candidate is
    # promoted. Reordering the returned audit never changes fixed 75 selection.
    count = len(candidates)
    max_probes = max(0, int(max_probes))
    cycles = max(1, (count + max(1, max_probes) - 1) // max(1, max_probes))
    cycle = (now.date().toordinal() % cycles) if count else 0
    start_index = min(cycle * max_probes, count)
    to_probe = candidates[start_index:start_index + max_probes]
    results = []
    for raw in to_probe:
        if getattr(client, "max_requests", None) is not None and (
            client.max_requests - client.request_count <
            3 * settings.max_pages + 25
        ):
            break
        results.append(probe_candidate(client, raw, settings, now=now))
    return {
        "rotation_cycle": cycle,
        "rotation_cycles": cycles,
        "rotation_start_index": start_index,
        "candidate_pool_size": count,
        "generated_at_utc": now.isoformat(),
        "known_repository_count": len(known_ids),
        "discovered_eligible_candidates": len(candidates),
        "probed": len(results),
        "verified_candidates": sum(
            r["verdict"] == "verified_candidate" for r in results),
        "requests_used": getattr(client, "request_count", 0) - before,
        "search_errors": search_errors,
        "results": results,
        "notice": (
            "Search/discovery and sampled source screening are not an approved "
            "change to the 75-repository cohort. Only a verified candidate is "
            "eligible for subsequent human-reviewed promotion; original "
            "records and historic cohort remain untouched."
        ),
    }


def main():
    cfg = Settings.from_env()
    with __import__("gzip").open(SNAPSHOT_PATH, "rt", encoding="utf-8") as file:
        snapshot = json.load(file)
    known = {
        int(r["repository"]["id"]) for r in snapshot.get("reports") or []
    }
    client = GitHubClient(cfg.github_token, cfg.timeout_seconds, cfg.max_retries,
                          max_requests=int(os.getenv("CANDIDATE_REQUEST_BUDGET", "220")))
    result = audit_candidates(
        client, cfg, known,
        max_candidates=int(os.getenv("CANDIDATE_POOL_LIMIT", "32")),
        max_probes=int(os.getenv("CANDIDATE_PROBE_LIMIT", "8")))
    destination = Path(os.getenv("CANDIDATE_AUDIT_OUT", "candidate-verified-audit.json"))
    destination.write_text(json.dumps(result, indent=2, sort_keys=True),
                           encoding="utf-8")
    print("VERIFIED CANDIDATE AUDIT:", json.dumps({
        "discovered": result["discovered_eligible_candidates"],
        "probed": result["probed"],
        "verified_candidates": result["verified_candidates"],
        "requests_used": result["requests_used"],
        "path": str(destination),
    }))
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as file:
            file.write("\n### Independent candidate verification (not promoted)\n\n")
            file.write(
                f"Discovered: **{result['discovered_eligible_candidates']}**, "
                f"rotating group **{result['rotation_cycle']+1}/{result['rotation_cycles']}**, "
                f"probed: **{result['probed']}**, "
                f"strictly verified: **{result['verified_candidates']}**. "
                "No existing repository was deleted or replaced.\n\n"
            )
            for item in result["results"]:
                file.write(
                    f"- `{item['full_name']}`: **{item['verdict']}** · "
                    + ", ".join(
                        f"{s}: {item['sources'].get(s, {}).get('status', 'not_checked')}"
                        for s in SOURCES
                    ) + "\n"
                )


if __name__ == "__main__":
    main()
