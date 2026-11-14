"""P2.2 view-state regressions; no synthetic records enter production charts."""
from src.ui.pages import _prepare_repo_picker, _reset_page_on_results_change


def test_repository_picker_follows_choice_across_pages_but_not_over_user_input():
    names = ["sample/alpha", "sample/beta"]
    state = {
        "active_repo": "sample/beta",
        "v2_details_repo": "sample/alpha",
        "_last_repo_picker": "v2_details_repo",
    }
    # On the same screen preserve the selectbox selection until its
    # on_change callback updates shared active_repo.
    assert _prepare_repo_picker(state, names, "v2_details_repo", names[0]) == 0
    state["v2_details_repo"] = names[1]
    state["active_repo"] = names[1]  # event callback
    assert _prepare_repo_picker(state, names, "v2_details_repo", names[0]) == 1

    # A previously visited page may have a stale selectbox value.
    state["v2_issues_repo"] = names[0]
    assert _prepare_repo_picker(state, names, "v2_issues_repo", names[0]) == 1
    assert "v2_issues_repo" not in state  # picker initializes from current global choice

    # Switching global Verified/Exploratory scope can invalidate a repository.
    state["active_repo"] = "sample/missing"
    state["v2_issues_repo"] = "sample/missing"
    assert _prepare_repo_picker(state, names, "v2_issues_repo", names[0]) == 0
    assert "v2_issues_repo" not in state


def test_pagination_resets_only_when_actual_filter_results_change():
    key = "v2_issues_page"
    rows = [
        {"url": f"https://github.com/sample/repo/issues/{i}", "number": i}
        for i in range(1, 35)
    ]
    state = {key: 3}
    _reset_page_on_results_change(state, rows, key)
    assert key not in state  # results introduced: reset to first page

    state[key] = 3
    _reset_page_on_results_change(state, rows, key)
    assert state[key] == 3  # same filter results: retain page

    _reset_page_on_results_change(state, rows[:3], key)
    assert key not in state  # fewer matches: clear out-of-range page

    state[key] = 1
    _reset_page_on_results_change(state, list(reversed(rows[:3])), key)
    assert key not in state  # even same size with changed sort/order


def test_pagination_identity_is_based_on_record_urls_not_displayed_labels():
    key = "v2_pr_page"
    state = {}
    original = [{"url": "https://github.com/sample/project/pull/1",
                 "title": "Title changed later", "number": 1}]
    _reset_page_on_results_change(state, original, key)
    state[key] = 1
    same_record = [{**original[0], "title": "Updated title"}]
    _reset_page_on_results_change(state, same_record, key)
    assert state[key] == 1
    replaced = [{**original[0], "url": "https://github.com/sample/project/pull/2"}]
    _reset_page_on_results_change(state, replaced, key)
    assert key not in state


def test_dashboard_never_labels_global_verified_cohort_as_all_tracked():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] /
              "src/ui/dashboard_v2.py").read_text(encoding="utf-8")
    assert 'is_all_tracked = global_scope.startswith("All tracked")' in source
    assert 'else "All projects in verified cohort"' in source
    assert 'if (mode == all_label' in source
    assert "a 28-day activity filter requires its own verified" in source


def test_independent_open_backlog_coverage_never_crashes_or_claims_issue_scan():
    from src.ui.pages import source_coverage_rows
    row = {
        "coverage": {"issues": None, "pull_requests": None,
                     "workflow_runs": None, "open_backlog": None},
        "status": {"issues": "partial", "pull_requests": "complete",
                   "workflow_runs": "stale"},
        "open_backlog_status": "unavailable",
    }
    display = {x["Source"]: x for x in source_coverage_rows(row)}
    assert display["Issues"]["Status"] == "partial"
    assert display["Pull Requests"]["Status"] == "complete"
    assert display["Workflow Runs"]["Status"] == "stale"
    assert display["Open Backlog"]["Status"] == "unavailable"
    assert display["Open Backlog"]["Last success"] == "Not available"
    row["open_backlog_status"] = "complete"
    assert {x["Source"]: x for x in source_coverage_rows(row)}[
        "Open Backlog"]["Status"] == "complete"
    assert {x["Source"]: x for x in source_coverage_rows(row)}[
        "Issues"]["Status"] == "partial"


def test_original_pr_table_handles_missing_pandas_nat_dates():
    import pandas as pd
    from datetime import datetime, timezone
    from src.ui.pages import _display_table_date
    assert _display_table_date(None) == "—"
    assert _display_table_date(pd.NaT) == "—"
    assert _display_table_date(pd.Timestamp("2026-11-13T01:00:00Z")) == "13 Nov 2026"
    assert _display_table_date("2026-11-12T00:00:00Z") == "12 Nov 2026"
    assert _display_table_date(datetime(2026, 11, 11, tzinfo=timezone.utc)) == "11 Nov 2026"
    values = pd.Series([pd.Timestamp("2026-11-13T01:00:00Z"), pd.NaT])
    assert values.map(_display_table_date).tolist() == ["13 Nov 2026", "—"]
