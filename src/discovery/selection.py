"""Auditable and deliberately non-representative sample selection."""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from src.config.settings import LANGUAGE_GROUPS, SEARCH_QUERIES, Settings
from src.database.models import Candidate, Repository, SelectionRun, utcnow
from src.database.store import upsert_repository
from src.collectors.client import GitHubClient, GitHubAPIError


def parse_dt(value: str | None):
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def validate_candidate(repo: dict, now: datetime, freshness_days: int = 90) -> str | None:
    if repo.get("private", False): return "private"
    if repo.get("fork", False): return "fork"
    if repo.get("archived", False): return "archived"
    if repo.get("stargazers_count", 0) < 50: return "below initial star filter"
    pushed = parse_dt(repo.get("pushed_at"))
    if not pushed or pushed < now - timedelta(days=freshness_days): return "inactive within observation filter"
    if not repo.get("has_issues", False): return "issues disabled"
    if not repo.get("id") or not repo.get("html_url") or not repo.get("full_name"): return "missing stable metadata"
    if repo.get("language") not in LANGUAGE_GROUPS: return "uncategorized language"
    return None


def deduplicate(candidates: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for item in candidates:
        if item.get("id") not in seen:
            seen.add(item.get("id"))
            result.append(item)
    return result


def category(repo: dict) -> str:
    return LANGUAGE_GROUPS.get(repo.get("language"), "Other")


def size_tier(repo: dict) -> str:
    stars = int(repo.get("stargazers_count", 0))
    return "small" if stars < 500 else "medium" if stars < 5000 else "large"


def diversified_sample(repos: list[dict], limit=20) -> list[dict]:
    """Round-robin over category AND size; intentionally not a quality ranking."""
    buckets = {}
    for r in repos:
        buckets.setdefault((category(r), size_tier(r)), []).append(r)
    for values in buckets.values():
        values.sort(key=lambda v: (v.get("pushed_at") or "", v.get("id", 0)), reverse=True)
    chosen: list[dict] = []
    cat_counter = Counter()
    cats = {category(r) for r in repos}
    max_per_cat = max(2, (limit + max(len(cats), 1) - 1) // max(len(cats), 1) + 1)
    while len(chosen) < limit:
        progress = False
        for key in sorted(buckets):
            if len(chosen) >= limit: break
            if cat_counter[key[0]] >= max_per_cat or not buckets[key]: continue
            item = buckets[key].pop(0)
            chosen.append(item)
            cat_counter[key[0]] += 1
            progress = True
        if not progress: break
    # A diversity preference must not needlessly drop eligible projects when
    # fewer categories are present than expected. Fill remaining slots with
    # audited eligible candidates after the balanced first pass.
    if len(chosen) < limit:
        remaining = [v for bucket in buckets.values() for v in bucket]
        remaining.sort(key=lambda v: (v.get("pushed_at") or "", v.get("id", 0)), reverse=True)
        chosen.extend(remaining[:limit - len(chosen)])
    return chosen


def probe_activity(client: GitHubClient, full_name: str) -> str | None:
    """Require standalone issues AND PRs. A bounded probe may reject uncertain repos."""
    issues, _ = client.get(f"/repos/{full_name}/issues", {"state": "all", "per_page": 10})
    prs, _ = client.get(f"/repos/{full_name}/pulls", {"state": "all", "per_page": 1})
    if not any("pull_request" not in issue for issue in issues):
        return "no standalone issues in bounded probe (not proof none exist)"
    if not prs: return "no pull requests in bounded probe"
    return None


def select_repositories(client: GitHubClient, session: Session, settings: Settings, now: datetime | None = None) -> dict:
    now = now or utcnow()
    run = SelectionRun(started_at=now, parameters={
        "search_queries": list(SEARCH_QUERIES), "stars_min": 50,
        "freshness_days": settings.freshness_days, "max_candidates": settings.max_candidates,
        "max_repos": settings.max_repos, "search_pages": settings.search_pages,
        "selection": "round-robin across primary-language group and stars tier",
        "source": "GitHub REST Search API /search/repositories",
    })
    session.add(run)
    session.commit()
    gathered = []
    errors = []
    cutoff = (now - timedelta(days=settings.freshness_days)).strftime("%Y-%m-%d")
    per_query_quota = max(3, (settings.max_candidates + len(SEARCH_QUERIES) - 1) // len(SEARCH_QUERIES))
    for base_query in SEARCH_QUERIES:
        query = f"{base_query} is:public fork:false archived:false stars:>=50 pushed:>={cutoff}"
        collected_for_query = 0
        # Bound per-language search so one ecosystem cannot consume all candidates.
        per_page = min(30, per_query_quota)
        for page in range(1, settings.search_pages + 1):
            try:
                data, _ = client.get("/search/repositories", {"q": query, "per_page": per_page, "page": page, "sort": "updated", "order": "desc"})
            except GitHubAPIError as exc:
                errors.append(f"{base_query}: {type(exc).__name__}")
                break
            if data.get("incomplete_results"):
                errors.append(f"{base_query}: Search API reports incomplete results")
            batch = data.get("items", [])
            available = min(per_query_quota - collected_for_query, settings.max_candidates - len(gathered))
            gathered.extend(batch[:available])
            collected_for_query += min(len(batch), available)
            if len(batch) < per_page or collected_for_query >= per_query_quota or len(gathered) >= settings.max_candidates: break
        if len(gathered) >= settings.max_candidates: break
    unique = deduplicate(gathered)[:settings.max_candidates]
    filtered = []
    reasons = {}
    for repo in unique:
        reason = validate_candidate(repo, now, settings.freshness_days)
        if not reason:
            try: reason = probe_activity(client, repo["full_name"])
            except GitHubAPIError: reason = "eligibility probe failed"
        if reason: reasons[repo["id"]] = reason
        else: filtered.append(repo)
    chosen = diversified_sample(filtered, settings.max_repos)
    chosen_ids = {r["id"] for r in chosen}
    for repo in unique:
        selected = repo["id"] in chosen_ids
        decision = "selected" if selected else "rejected"
        reason = "met activity filters; category/size diversified" if selected else reasons.get(repo["id"], "valid but outside sample cap/diversity limit")
        session.add(Candidate(selection_run_id=run.id, repo_id=repo["id"], full_name=repo["full_name"], url=repo["html_url"], category=category(repo), stars=repo.get("stargazers_count", 0), decision=decision, reason=reason))
        if selected:
            upsert_repository(session, {
                "id": repo["id"], "full_name": repo["full_name"], "owner": repo["owner"]["login"],
                "name": repo["name"], "url": repo["html_url"], "language": repo.get("language"),
                "category": category(repo), "stars": repo["stargazers_count"],
                "created_at": parse_dt(repo.get("created_at")), "pushed_at": parse_dt(repo.get("pushed_at")),
                "default_branch": repo.get("default_branch", "main"), "is_fork": False,
                "archived": False, "selected": True, "selected_at": now, "selection_run_id": run.id,
            })
    run.candidate_count = len(unique)
    run.accepted_count = len(chosen)
    run.completed_at = utcnow()
    run.status = "partial" if errors else "complete"
    run.notes = "; ".join(errors) if errors else ("Eligible candidates fewer than target" if len(chosen) < settings.max_repos else None)
    session.commit()
    return {"selection_run": run.id, "candidates": len(unique), "eligible": len(filtered), "selected": [r["full_name"] for r in chosen], "errors": errors}
