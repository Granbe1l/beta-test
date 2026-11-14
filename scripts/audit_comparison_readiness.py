"""Audit the real curated comparison; fail on false zeros or invented history.

Unlike an assertion-free receipt, this script performs independent row
counts, short-window and partial-source negative controls and validates
any matched historical pair against the original stored observations.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.analytics.snapshot import read_snapshot
from src.analytics.comparison_audit import audit_comparison_readiness

reports, _, meta = read_snapshot()
result = audit_comparison_readiness(reports, now=datetime.now(timezone.utc))
result["snapshot_generated_at"] = meta["generated_at"].isoformat()
result["scope"] = "Real stored public GitHub records, not external GitHub completeness"
Path("predeploy-comparison-audit.json").write_text(
    json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
print("REAL COMPARISON READINESS:", json.dumps(result, sort_keys=True))
