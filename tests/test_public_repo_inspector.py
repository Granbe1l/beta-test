"""Project-manager URL inspection: network safety, evidence labels, and no cohort writes."""
from datetime import datetime, timezone
import pytest

from src.analytics.on_demand import (
    PublicLookupError, inspect_public_repository, parse_public_repo,
)

NOW = datetime(2026, 11, 14, 0, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize("raw, expected", [
    ("Granbe1l/beta-test", "Granbe1l/beta-test"),
    ("https://github.com/Granbe1l/beta-test", "Granbe1l/beta-test"),
    ("https://github.com/Granbe1l/beta-test.git", "Granbe1l/beta-test"),
])
def test_public_link_parser_accepts_repo_roots(raw, expected):
    assert parse_public_repo(raw) == expected


@pytest.mark.parametrize("raw", [
    "", "not-a-repo", "https://github.com/org/repo/issues/2",
    "https://evil.github.com/org/repo", "https://github.com.evil.test/org/repo",
    "http://github.com/org/repo", "file:///etc/passwd",
    "https://github.com@evil.example/org/repo",
    "https://github.com:8443/org/repo", "https://github.com/org/../repo",
    "https://github.com/org/repo?token=x", "https://github.com/org/repo#issue",
    "https://127.0.0.1/org/repo", "https://github.com/org/%2e%2e",
])
def test_parser_rejects_untrusted_hosts_and_non_root_paths(raw):
    with pytest.raises(PublicLookupError):
        parse_public_repo(raw)


class FakeResponse:
    def __init__(self, value=None, status_code=200):
        self.value = value
        self.status_code = status_code

    def json(self):
        return self.value


def sample_calls():
    base = "https://api.github.com/repos/example/project"
    return {
        base: FakeResponse({
            "full_name": "example/project", "private": False,
            "html_url": "https://github.com/example/project",
            "description": "A real public GitHub project",
            "language": "Python", "stargazers_count": 99,
            "pushed_at": "2026-11-13T20:00:00Z",
            "default_branch": "main",
        }),
        base + "/issues?state=all&sort=updated&direction=desc&per_page=30":
            FakeResponse([
                {"number": 1, "title": "Open task", "state": "open",
                 "created_at": "2026-08-01T00:00:00Z",
                 "html_url": "https://github.com/example/project/issues/1"},
                {"number": 2, "state": "open", "pull_request": {"url": "pr"}},
            ]),
        base + "/pulls?state=all&sort=updated&direction=desc&per_page=30":
            FakeResponse([{"number": 2, "state": "closed", "merged_at": "2026-11-13T20:00:00Z",
                           "created_at": "2026-11-12T20:00:00Z",
                           "html_url": "https://github.com/example/project/pull/2"}]),
        base + "/actions/runs?per_page=30":
            FakeResponse({"workflow_runs": [
                {"name": "CI", "status": "completed", "conclusion": "failure",
                 "html_url": "https://github.com/example/project/actions/runs/9"},
                {"name": "CI", "status": "completed", "conclusion": "success"},
                {"name": "CI", "status": "queued", "conclusion": None},
            ]}),
    }


def test_preview_makes_only_four_fixed_host_calls_and_never_claims_verified():
    response_map = sample_calls()
    calls = []

    def get(url, **kwargs):
        calls.append((url, kwargs))
        return response_map[url]

    report = inspect_public_repository(
        "https://github.com/example/project", get=get, now=NOW)
    assert len(calls) == 4
    assert all(url.startswith("https://api.github.com/repos/example/project")
               for url, _ in calls)
    assert all(options["allow_redirects"] is False for _, options in calls)
    assert all("Authorization" not in options["headers"] for _, options in calls)
    assert report["name"] == "example/project"
    assert len(report["sample_issues"]) == 1  # GitHub /issues also returns PRs
    assert report["sample_open_issues"] == 1
    assert report["sample_old_issues"] == 1
    assert report["sample_ci_failed"] == 1
    assert report["sample_ci_completed"] == 2
    assert report["sample_merged_median_hours"] == 24
    assert report["verified_28d"] is False
    assert report["member_of_curated_75"] is False


def test_private_repository_is_rejected_with_safe_message():
    mapping = sample_calls()
    first = next(iter(mapping))
    mapping[first] = FakeResponse(status_code=404)

    with pytest.raises(PublicLookupError, match="not found or not public"):
        inspect_public_repository(
            "example/project", get=lambda url, **kw: mapping[url], now=NOW)


def test_rate_limited_source_does_not_masquerade_as_zero_or_full_window():
    mapping = sample_calls()
    issue_key = next(key for key in mapping if "/issues?" in key)
    mapping[issue_key] = FakeResponse(status_code=403)
    report = inspect_public_repository(
        "example/project", get=lambda url, **kw: mapping[url], now=NOW)
    assert report["issues_error"] == "rate-limited or restricted"
    assert report["sample_issues"] == []
    assert report["verified_28d"] is False
