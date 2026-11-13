"""Re-audit second-wave source-screened replacement prospects using real GitHub REST.

These names were screened individually for public metadata and plausible
28-day Issues, PR and Actions volume. This is purposive portfolio curation,
NOT a representative sample or sufficient proof until all sources complete.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.audit_candidate_pool import probe_candidate
from src.collectors.client import GitHubClient
from src.config.settings import Settings
from src.discovery.selection import validate_candidate

TARGETS = (
    "terraform-docs/terraform-docs",
    "flipt-io/flipt",
    "squidowl/halloy",
    "breezy-weather/breezy-weather",
    "T8RIN/ImageToolbox",
    "iamgio/quarkdown",
    "maxrave-dev/SimpMusic",
    "usesend/useSend",
    "formkit/formkit",
    "surveyjs/survey-library",
    "dmno-dev/varlock",
)


def audit_targets(client, cfg, *, now=None, target_names=TARGETS):
    now = now or datetime.now(timezone.utc)
    results = []
    for name in target_names:
        try:
            raw, _ = client.get("/repos/" + name)
            created = datetime.fromisoformat(raw["created_at"].replace("Z", "+00:00"))
            invalid = (
                raw.get("full_name") != name
                or validate_candidate(raw, now, cfg.freshness_days) is not None
                or created > now - timedelta(days=29)
            )
            if invalid:
                results.append({"full_name": name, "verdict": "not_verified",
                                "sources": {}, "reason": "current_metadata_or_eligibility"})
                continue
            audited = probe_candidate(client, raw, cfg, now=now)
            results.append(audited)
        except Exception as exc:
            results.append({"full_name": name, "verdict": "not_verified",
                            "sources": {}, "reason": type(exc).__name__})
    return {
        "generated_at_utc": now.isoformat(),
        "selection_method": "explicit targeted source investigation; not random sampling",
        "probed": len(results),
        "verified_candidates": sum(x["verdict"] == "verified_candidate" for x in results),
        "results": results,
        "requests_used": client.request_count,
    }


def main():
    cfg = Settings.from_env()
    api = GitHubClient(cfg.github_token, cfg.timeout_seconds, cfg.max_retries,
                       max_requests=int(os.getenv("TARGET_AUDIT_REQUEST_BUDGET", "280")))
    report = audit_targets(api, cfg)
    out = Path("target-candidate-verified-audit.json")
    out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print("TARGETED VERIFIED AUDIT", json.dumps({
        "probed": report["probed"],
        "verified_candidates": report["verified_candidates"],
        "requests_used": report["requests_used"],
        "file": str(out),
    }))
    for item in report["results"]:
        print(item["full_name"], item["verdict"],
              {k: (v.get("status"), v.get("records")) for k, v in item.get("sources", {}).items()})
    if report["verified_candidates"] == 0:
        raise SystemExit("Zero verified candidates: refusing cohort mutation")


if __name__ == "__main__":
    main()
