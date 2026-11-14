"""Read-only, formula-safe CSV export for a bounded external GitHub inspection."""
from __future__ import annotations

import csv
from io import StringIO


def _safe(value) -> str:
    val = str(value if value is not None else "").replace("\x00", "")
    return "'" + val if val.lstrip().startswith(("=", "+", "-", "@")) else val


def inspection_csv(data: dict, analysis: dict) -> bytes:
    stream = StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(["Repository", "Observed at UTC", "Section", "Measure",
                     "Observed value", "Scope / next check", "GitHub URL"])
    repo = _safe(data.get("name", ""))
    timestamp = _safe(data.get("observed_at", ""))
    link = _safe(data.get("html_url", ""))

    def add(section, measure, value, limit, url=""):
        writer.writerow([repo, timestamp, _safe(section), _safe(measure),
                         _safe(value), _safe(limit), _safe(url)])

    add("Context", "Inspection mode", "External public GitHub sample",
        "NOT a member of the 50 curated/Verified projects. "
        "At most 30 recently updated records per source; not a complete 28-day "
        "history, backlog, SLA, or project-health score.", link)
    source_specs = [
        ("Issues", "Observed open Issues in sample", "sample_open_issues",
         "issues_error"),
        ("Pull requests", "Recently updated PR records in sample",
         None, "prs_error"),
        ("CI/CD", "Failed or timed out CI runs in sample",
         "sample_ci_failed", "ci_error"),
    ]
    for title, measure, field, error_field in source_specs:
        error = data.get(error_field)
        if error:
            add(title, measure, "",
                "SOURCE UNAVAILABLE: " + str(error) + ". Unknown, not zero.",
                link)
        else:
            value = len(data.get("sample_prs") or []) if field is None else data.get(field)
            add(title, measure, value,
                "Observed latest API sample only; no full-backlog or 28-day coverage claim.",
                link)
    for index, finding in enumerate(analysis.get("review_plan") or [], 1):
        add("Inspection step " + str(index), finding.get("title", ""),
            finding.get("tag", ""),
            finding.get("explanation", ""),
            finding.get("url") or link)
    return stream.getvalue().encode("utf-8-sig")
