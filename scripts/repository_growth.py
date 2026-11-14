"""Read-only, single-call GitHub repository growth diagnostic.

GitHub's 'size' field is approximate and may lag. It is NOT a measurement
of local Git history size or a proof of optimized binary storage.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import urllib.request

REPO = "Granbe1l/beta-test"
ENDPOINT = f"https://api.github.com/repos/{REPO}"
WARN_MIB = 200


def evaluate(repo_size_kib: int, snapshot_bytes: int, warn_mib: int = WARN_MIB):
    if repo_size_kib < 0 or snapshot_bytes < 0 or warn_mib < 1:
        raise ValueError("Size and warning threshold must be valid")
    return {
        "repo": REPO,
        "api_repo_size_kib": repo_size_kib,
        "approx_repo_size_mib": round(repo_size_kib / 1024, 2),
        "current_snapshot_bytes": snapshot_bytes,
        "warning_threshold_mib": warn_mib,
        "warning": repo_size_kib >= warn_mib * 1024,
        "measurement_limits": (
            "GitHub repository API size is approximate and can lag; repeated "
            "compressed binary snapshot commits may grow Git history, but "
            "growth per refresh cannot be extrapolated from a single sample."
        ),
    }


def main():
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "delivery-monitor-repository-footprint-audit",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(ENDPOINT, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as response:
        metadata = json.load(response)
    size = metadata.get("size")
    if not isinstance(size, int):
        raise RuntimeError("GitHub repository size missing; no fake size emitted")
    snapshot = Path("data/github_public_snapshot.json.gz")
    if not snapshot.is_file():
        raise RuntimeError("Committed snapshot missing")
    report = evaluate(size, snapshot.stat().st_size)
    Path("repository-growth-audit.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("Repository size audit:", json.dumps(report, sort_keys=True))
    if report["warning"]:
        print(
            f"::warning::Repository size is at or above {WARN_MIB} MiB "
            "by the approximate GitHub API measurement. Review binary growth."
        )


if __name__ == "__main__":
    main()
