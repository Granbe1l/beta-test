"""Inventory status is independent of 28-day event verification."""
from scripts.triage_open_inventory import triage_inventory


def row(name, status, *, last=None, error=None):
    return {
        "name": name,
        "open_backlog_status": status,
        "source_details": {
            "issues": {"status": "complete"},
            "pull_requests": {"status": "complete"},
            "workflow_runs": {"status": "complete"},
            "open_backlog": {
                "last_success_at": last, "pages_fetched": 6,
                "records_fetched": 450, "last_error": error,
            } if status != "unavailable" else None,
        },
    }


def test_actual_gap_statuses_and_five_never_verified_are_exposed():
    reports = [row(f"sample/verified-{i}", "complete") for i in range(41)]
    reports += [
        row(f"sample/stale-{i}", "stale", last="2026-11-13 01:00:00")
        for i in range(4)
    ]
    reports += [row(f"sample/unvisited-{i}", "unavailable") for i in range(5)]
    result = triage_inventory({"repositories": reports})
    assert result["total_selected_repositories"] == 50
    assert result["fresh_full_open_inventories"] == 41
    assert result["not_fresh_or_not_verified"] == 9
    assert result["all_full_open_inventories_current"] is False
    assert [v["inventory_status"] for v in result["gaps"]].count("stale") == 4
    assert [v["inventory_status"] for v in result["gaps"]].count("unavailable") == 5
    assert all(
        "full-open inventory" in v["reason"] or "exhausted list" in v["reason"]
        for v in result["gaps"]
    )


def test_complete_checkpoint_and_partial_page_cap_are_not_conflated():
    reports = [
        row("sample/a", "partial", error="Page cap reached"),
        row("sample/b", "failed", error="HTTP 429"),
        row("sample/c", "complete"),
    ]
    result = triage_inventory({"repositories": reports})
    assert result["fresh_full_open_inventories"] == 1
    assert result["not_fresh_or_not_verified"] == 2
    assert result["gaps"][0]["inventory_status"] == "failed"
    assert result["gaps"][1]["inventory_status"] == "partial"
    assert "Page cap reached" in result["gaps"][1]["last_error"]


def test_empty_report_is_never_called_50_of_50():
    result = triage_inventory({"repositories": []})
    assert result["fresh_full_open_inventories"] == 0
    assert result["all_full_open_inventories_current"] is False


def test_repeated_or_bad_repo_name_never_silently_counts_as_complete():
    try:
        triage_inventory({"repositories": [{"name": ""}]})
    except ValueError:
        pass
    else:
        raise AssertionError("Malformed audit row must not count as verified")
