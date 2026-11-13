"""Proposed replacement is never an automatic dataset mutation."""
from datetime import datetime, timedelta, timezone
from scripts.replacement_plan import proposed_swaps

NOW = datetime(2026, 11, 13, 3, tzinfo=timezone.utc)


def report(name, rid, *, verified=True, stars=200, category="Data & backend"):
    return {
        "repository": {
            "id": rid, "full_name": name, "stars": stars,
            "category": category,
        },
        "status": {
            source: "complete" if verified else "partial"
            for source in ("issues", "pull_requests", "workflow_runs")
        },
        "coverage": {
            source: {
                "coverage_start": NOW-timedelta(days=35),
                "last_success_at": NOW,
            }
            for source in ("issues", "pull_requests", "workflow_runs")
        },
    }


def audit(name="org/candidate", created=None, *, status="verified_28d",
          verdict="verified_candidate", size="small", cat="Data & backend"):
    created = created or NOW
    return {
        "generated_at_utc": created.isoformat(),
        "results": [{
            "github_id": 202,
            "full_name": name,
            "url": f"https://github.com/{name}",
            "category": cat,
            "size_tier": size,
            "verdict": verdict,
            "sources": {
                source: {"status": status, "records": 10}
                for source in ("issues", "pull_requests", "workflow_runs")
            },
        }],
    }


def test_verified_candidate_proposes_diversity_matched_unapproved_swap():
    reports = [
        report("org/already-verified", 101, verified=True),
        report("org/partial", 102, verified=False),
    ]
    result = proposed_swaps(reports, audit(), now=NOW)
    assert result["verified_originals_28d"] == 1
    assert result["tracked_original_repositories_unchanged"] == 2
    assert result["changes_applied"] == 0
    assert len(result["proposed_unapproved_swaps"]) == 1
    proposal = result["proposed_unapproved_swaps"][0]
    assert proposal["exclude_from_future_active_cohort_only"] == "org/partial"
    assert proposal["candidate_name"] == "org/candidate"
    assert proposal["approved"] is False
    assert reports[1]["repository"]["id"] == 102


def test_stale_candidate_evidence_cannot_generate_promotion():
    result = proposed_swaps(
        [report("org/partial", 102, verified=False)],
        audit(created=NOW-timedelta(hours=13)),
        now=NOW)
    assert not result["candidate_evidence_fresh"]
    assert result["proposed_unapproved_swaps"] == []
    assert result["changes_applied"] == 0


def test_partial_source_does_not_pass_even_if_verdict_claims_verified():
    result = proposed_swaps(
        [report("org/partial", 102, verified=False)],
        audit(status="partial_or_short_window"), now=NOW)
    assert result["proposed_unapproved_swaps"] == []
    assert result["rejected_candidates"][0]["reason"] == "candidate_not_currently_verified"


def test_mismatched_size_or_category_never_silently_replaces_repo():
    result = proposed_swaps(
        [report("org/partial", 102, verified=False, stars=8000)],
        audit(), now=NOW)
    assert not result["proposed_unapproved_swaps"]
    assert result["rejected_candidates"][0]["reason"] == "no_matching_category_and_size"


def test_cannot_propose_replacement_of_existing_verified_repo():
    result = proposed_swaps(
        [report("org/already-verified", 101, verified=True)],
        audit(), now=NOW)
    assert not result["proposed_unapproved_swaps"]
