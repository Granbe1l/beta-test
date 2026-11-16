"""P0.3: refuse redundant dispatch collection using the *latest main* snapshot.

This is a safety preflight, NOT a new scheduler. It intentionally leaves
native 'schedule' and workflow-definition 'push' collection unchanged.
For workflow_dispatch (Cloudflare rescue / GitHub watchdog / user), inspect
the current committed snapshot immediately before heavy work. A queued
rescue may no longer be necessary after another validated collector publishes.

Source files, curated cohort and verified evidence gates are never edited.
"""
from __future__ import annotations

from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import re

SNAPSHOT_PATH = Path("/tmp/p0-current-main-snapshot.json.gz")
RECEIPT = Path("collector-dispatch-preflight.json")
# Match the currently deployed, owner-managed Cloudflare 6h emergency policy.
# Do not silently change this to a 4h new primary schedule.
EMERGENCY_AGE_HOURS = 6
FUTURE_TOLERANCE_MINUTES = 15
EVENTS_WITH_ALWAYS_ON_INGESTION = frozenset({"push", "schedule"})


def utc_time(raw: str) -> datetime:
    if not isinstance(raw, str) or not raw:
        raise ValueError("missing_snapshot_generated_at")
    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("snapshot_timestamp_has_no_timezone")
    return parsed.astimezone(timezone.utc)


def read_generated_at(snapshot: Path) -> datetime:
    """Check committed JSON metadata only; never decode full records for gating."""
    with gzip.open(snapshot, "rb") as stream:
        first = stream.read(4096)
    match = re.search(rb'"generated_at"\s*:\s*"([^"]+)"', first)
    if match is None:
        raise ValueError("missing_committed_snapshot_generated_at")
    return utc_time(match.group(1).decode("ascii"))


def decide(*, event: str, force_refresh: bool, generated_at: datetime | None,
           now: datetime) -> dict:
    if now.tzinfo is None:
        raise ValueError("now_requires_timezone")
    now = now.astimezone(timezone.utc)
    if event in EVENTS_WITH_ALWAYS_ON_INGESTION:
        return {
            "should_collect": True,
            "reason": "native_or_workflow_change_always_collects",
            "event": event,
            "source_freshness_checked": False,
        }
    if event != "workflow_dispatch":
        raise ValueError("unexpected_collector_trigger")
    if force_refresh:
        return {
            "should_collect": True,
            "reason": "explicit_operator_force_refresh",
            "event": event,
            "source_freshness_checked": False,
        }
    if generated_at is None:
        raise ValueError("freshness_cannot_be_verified")
    age_minutes = (now - generated_at.astimezone(timezone.utc)).total_seconds() / 60
    if age_minutes < -FUTURE_TOLERANCE_MINUTES:
        raise ValueError("committed_snapshot_timestamp_unreasonably_in_future")
    age_minutes = max(0, age_minutes)
    stale = age_minutes > EMERGENCY_AGE_HOURS * 60
    return {
        "should_collect": stale,
        "reason": "stale_current_main_snapshot" if stale else "fresh_current_main_snapshot",
        "event": event,
        "source_freshness_checked": True,
        "current_main_generated_at_utc": generated_at.astimezone(timezone.utc).isoformat(),
        "evaluated_at_utc": now.isoformat(),
        "snapshot_age_minutes": round(age_minutes, 2),
        "threshold_minutes": EMERGENCY_AGE_HOURS * 60,
        "note": "A skipped rescue is not a successful source scan or native scheduled run.",
    }


def main() -> None:
    event = os.environ.get("GITHUB_EVENT_NAME", "")
    forced = os.environ.get("FORCE_REFRESH", "false").lower() == "true"
    generated_at = (
        read_generated_at(Path(os.environ.get("P0_CURRENT_MAIN_SNAPSHOT", str(SNAPSHOT_PATH))))
        if event == "workflow_dispatch" and not forced else None
    )
    decision = decide(event=event, force_refresh=forced, generated_at=generated_at,
                      now=datetime.now(timezone.utc))
    RECEIPT.write_text(json.dumps(decision, sort_keys=True, indent=2) + "\n",
                       encoding="utf-8")
    output = os.getenv("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as f:
            f.write("should_collect=" + str(decision["should_collect"]).lower() + "\n")
    print("P0 COLLECTOR DISPATCH PREFLIGHT:", json.dumps(decision, sort_keys=True), flush=True)
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("### P0 collector dispatch preflight\n\n")
            f.write(f"Event: \`{event}\`. Decision: **{decision['reason']}**. "
                    f"Heavy collection: **{decision['should_collect']}**.\n\n")
            f.write("Dispatch skips never count as native scheduled scans or source verification.\n")


if __name__ == "__main__":
    main()
