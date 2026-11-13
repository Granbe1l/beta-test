"""One-minute reviewer guide: plain-language facts and honest data boundaries.

Usability copy is not evidence that 3–5 real nontechnical participants
understood the application. That is a separately required human study.
"""
from __future__ import annotations

TERMS = (
    ("Repository", "A public GitHub software project being observed."),
    ("Issue", "A reported task, question, or bug; it is not automatically overdue."),
    ("Pull request (PR)", "A proposal to change code. It is not finished until merged."),
    ("CI/CD check", "An automated build or test run; one failure is not proof the project failed."),
    ("Verified period", "GitHub data for the selected 7 or 28 days were fully scanned for all required sources. It is not a project-quality rating or a complete lifetime history."),
    ("Exploratory", "Only retrieved records are shown. Uncollected or stale records cannot be counted as zero activity."),
)
HOW_TO_READ = (
    "1. Read the selected time period and number of qualifying projects.",
    "2. Look for a measured finding, not a subjective project health score.",
    "3. Open the original GitHub record, inspect its context, and only then decide what to check next.",
)

NAV_HELP = {
    "Dashboard": "Start with observed activity, confidence and a source-backed inspection.",
    "Explore repositories": "Select or compare public software projects without ranking people.",
    "Open issues": "Inspect reported tasks, their observed ages and original GitHub records.",
    "Changes & reviews": "Explore proposed and merged code changes, not employee productivity.",
    "Build activity": "Inspect automated build/test results, not a software quality score.",
    "Key findings": "Review measured signals, GitHub evidence and what to inspect next.",
}

def guide_text() -> str:
    return "\n\n".join("**" + label + ":** " + meaning
                         for label, meaning in TERMS)
