"""Observed account-type metadata on captured PRs; NOT developer identity."""
from __future__ import annotations


def pr_account_type_counts(rows: list[dict]) -> dict[str, int]:
    counts = {"GitHub User-type account": 0, "GitHub Bot-type account": 0,
              "Other / unknown": 0}
    for row in rows:
        kind = row.get("author_type")
        if kind == "User":
            counts["GitHub User-type account"] += 1
        elif kind == "Bot":
            counts["GitHub Bot-type account"] += 1
        else:
            counts["Other / unknown"] += 1
    return counts


def pr_account_evidence(rows: list[dict]) -> dict:
    counts = pr_account_type_counts(rows)
    known = counts["GitHub User-type account"] + counts["GitHub Bot-type account"]
    return {
        "counts": counts, "known": known, "observed": len(rows),
        "coverage": known / len(rows) * 100 if rows else None,
        "scope": (
            "GitHub account metadata in collected PR records only; "
            "User-type does not prove a human authored the code. Unknown "
            "includes old records without captured author metadata. "
            "The account-type mix is not a quality, effort or "
            "developer-productivity ranking."
        ),
    }
