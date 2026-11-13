"""Read-only, bounded PUBLIC GitHub repository inspection.

Does not join or mutate the 75 audited projects. All output is explicitly
exploratory: a single page never certifies 28-day source completeness.
"""
from __future__ import annotations

from datetime import datetime, timezone
from statistics import median
from urllib.parse import urlsplit
import re

import requests

OWNER = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
REPO = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
API_BASE = "https://api.github.com"
MAX_ITEMS = 30


class PublicLookupError(ValueError):
    """Friendly, sanitized error; never show API credentials or raw response."""


def parse_public_repo(value: str) -> str:
    raw = (value or "").strip()
    if not raw or len(raw) > 300:
        raise PublicLookupError("Enter a public GitHub repository link or owner/repo.")
    if "://" in raw:
        parsed = urlsplit(raw)
        if (parsed.scheme != "https" or parsed.hostname != "github.com"
                or parsed.port is not None or parsed.username is not None
                or parsed.password is not None or parsed.query or parsed.fragment):
            raise PublicLookupError("Only https://github.com/owner/repo links are supported.")
        path = parsed.path.strip("/")
    else:
        if raw.startswith("/") or any(x in raw for x in ("?", "#", "\\", ":")):
            raise PublicLookupError("Use owner/repo or https://github.com/owner/repo.")
        path = raw.strip("/")
    parts = path.split("/")
    if len(parts) != 2:
        raise PublicLookupError("Provide the repository root, not an Issue, PR or file link.")
    owner, name = parts
    if name.endswith(".git"):
        name = name[:-4]
    if not OWNER.fullmatch(owner) or not REPO.fullmatch(name) or name in {".", ".."}:
        raise PublicLookupError("Invalid GitHub repository owner or name.")
    return owner + "/" + name


def _request(path: str, *, get, required=False):
    # Fixed GitHub API host, strict validated owner/repo, redirects disabled:
    # never proxy an arbitrary URL supplied by the dashboard visitor.
    try:
        response = get(
            API_BASE + path,
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "ProjectDeliveryMonitor-public-inspector",
            },
            timeout=8,
            allow_redirects=False,
        )
    except requests.RequestException:
        if required:
            raise PublicLookupError("GitHub could not be reached. Try again later.") from None
        return None, "temporarily unavailable"
    if response.status_code == 404:
        if required:
            raise PublicLookupError(
                "Repository not found or not public. Private repositories require a separate authenticated integration."
            )
        return None, "not available"
    if response.status_code in (403, 429):
        if required:
            raise PublicLookupError(
                "GitHub API rate limit or access restriction. Retry after the limit resets."
            )
        return None, "rate-limited or restricted"
    if response.status_code != 200:
        if required:
            raise PublicLookupError(
                "GitHub did not return repository details. HTTP " + str(response.status_code)
            )
        return None, "HTTP " + str(response.status_code)
    try:
        return response.json(), None
    except ValueError:
        if required:
            raise PublicLookupError("GitHub returned an unreadable response.") from None
        return None, "unreadable response"


def _recent_failure(rows):
    completed = [r for r in rows if r.get("status") == "completed"
                 and r.get("conclusion") not in (None, "skipped", "neutral")]
    failed = [r for r in completed if r.get("conclusion") in
              ("failure", "timed_out", "startup_failure", "action_required")]
    return completed, failed


def inspect_public_repository(value: str, *, get=None, now=None) -> dict:
    """Four capped GET requests max; no credentials and no persistent writes."""
    full_name = parse_public_repo(value)
    get = get or requests.get
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    path = "/repos/" + full_name
    metadata, _ = _request(path, get=get, required=True)
    if not isinstance(metadata, dict) or metadata.get("private") is True:
        raise PublicLookupError("Only public repository inspection is available.")
    canonical = metadata.get("full_name")
    if not isinstance(canonical, str) or canonical.casefold() != full_name.casefold():
        raise PublicLookupError("Repository metadata did not match the requested project.")

    issues_raw, issues_error = _request(
        path + "/issues?state=all&sort=updated&direction=desc&per_page=30", get=get)
    prs_raw, prs_error = _request(
        path + "/pulls?state=all&sort=updated&direction=desc&per_page=30", get=get)
    runs_raw, ci_error = _request(path + "/actions/runs?per_page=30", get=get)

    issue_events = [x for x in (issues_raw if isinstance(issues_raw, list) else [])
                    if isinstance(x, dict) and not x.get("pull_request")]
    prs = [x for x in (prs_raw if isinstance(prs_raw, list) else [])
           if isinstance(x, dict)]
    run_items = runs_raw.get("workflow_runs", []) if isinstance(runs_raw, dict) else []
    runs = [x for x in run_items if isinstance(x, dict)]
    completed, failed = _recent_failure(runs)

    # No complete open-backlog claim: /issues includes PR objects and this
    # endpoint only retrieves the most recently updated page.
    open_issues = [x for x in issue_events if x.get("state") == "open"]
    old_issues = []
    for row in open_issues:
        try:
            created = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
        except (ValueError, KeyError, AttributeError):
            continue
        if (now - created).days >= 30:
            old_issues.append(row)
    merged_hours = []
    for p in prs:
        if not p.get("merged_at"):
            continue
        try:
            created = datetime.fromisoformat(p["created_at"].replace("Z", "+00:00"))
            merged = datetime.fromisoformat(p["merged_at"].replace("Z", "+00:00"))
        except (ValueError, KeyError, AttributeError):
            continue
        if merged >= created:
            merged_hours.append((merged - created).total_seconds() / 3600)

    return {
        "name": canonical,
        "html_url": "https://github.com/" + canonical,
        "description": str(metadata.get("description") or "")[:300],
        "language": metadata.get("language") or "Unknown",
        "default_branch": metadata.get("default_branch") or "Unknown",
        "stars": metadata.get("stargazers_count"),
        "pushed_at": metadata.get("pushed_at"),
        "sample_issues": issue_events,
        "sample_prs": prs,
        "sample_runs": runs,
        "sample_open_issues": len(open_issues),
        "sample_old_issues": len(old_issues),
        "sample_merged_median_hours": median(merged_hours) if merged_hours else None,
        "sample_ci_completed": len(completed),
        "sample_ci_failed": len(failed),
        "last_failed_run_url": next((x.get("html_url") for x in failed if x.get("html_url")), None),
        "old_issue_url": next((x.get("html_url") for x in old_issues if x.get("html_url")), None),
        "issues_error": issues_error,
        "prs_error": prs_error,
        "ci_error": ci_error,
        "observed_at": now.isoformat(),
        "provenance": "Public GitHub REST API; at most 30 latest records per source",
        "verified_28d": False,
        "member_of_curated_75": False,
    }
