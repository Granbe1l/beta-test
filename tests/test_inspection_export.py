"""Evidence export protects source scope, completeness and Excel readers."""
from io import StringIO
import csv
from src.analytics.inspection_export import inspection_csv


def example():
    return {
        "name": "psf/requests", "observed_at": "2026-11-14T08:50:00+00:00",
        "html_url": "https://github.com/psf/requests",
        "sample_open_issues": 3,
        "sample_prs": [{"number": 1}, {"number": 2}],
        "sample_ci_failed": 1,
        "issues_error": None, "prs_error": None, "ci_error": None,
    }


def rows_for(data, checks=None):
    result = inspection_csv(data, {"review_plan": checks or []})
    assert result.startswith(b"\xef\xbb\xbf")
    return list(csv.DictReader(StringIO(result.decode("utf-8-sig"))))


def test_export_has_sample_scope_and_links_not_verified_28day():
    rows = rows_for(example(), [{
        "title": "Review checks", "tag": "Review next",
        "explanation": "Inspect failed workflow",
        "url": "https://github.com/psf/requests/actions/runs/5",
    }])
    assert len(rows) == 5
    assert rows[0]["Section"] == "Context"
    assert "NOT a member" in rows[0]["Scope / next check"]
    assert "not a complete 28-day" in rows[0]["Scope / next check"]
    assert next(row for row in rows if row["Section"] == "Issues")["Observed value"] == "3"
    assert next(row for row in rows if row["Section"] == "Pull requests")["Observed value"] == "2"
    assert next(row for row in rows if row["Section"] == "CI/CD")["Observed value"] == "1"
    assert rows[-1]["GitHub URL"].endswith("/actions/runs/5")


def test_export_preserves_unknown_api_not_zero():
    data = example()
    data.update(issues_error="rate limited", ci_error="HTTP 503")
    rows = rows_for(data)
    issue = next(row for row in rows if row["Section"] == "Issues")
    ci = next(row for row in rows if row["Section"] == "CI/CD")
    assert issue["Observed value"] == ""
    assert ci["Observed value"] == ""
    assert "Unknown, not zero" in ci["Scope / next check"]


def test_export_blocks_excel_formula_injection_in_source_titles():
    data = example()
    data["name"] = "=HYPERLINK(\"https://evil.example\")"
    checks = [{"title": "+DANGEROUS()", "tag": "@bad",
               "explanation": "-2+3", "url": ""}]
    rows = rows_for(data, checks)
    assert rows[0]["Repository"].startswith("'=")
    assert rows[-1]["Measure"].startswith("'+")
    assert rows[-1]["Observed value"].startswith("'@")
    assert rows[-1]["Scope / next check"].startswith("'-")
