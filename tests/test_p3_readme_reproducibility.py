"""P3: concise entry, faithful archival links and actual runtime receipts."""
from pathlib import Path
from importlib import metadata

import pytest

from scripts.record_runtime_environment import make_receipt

ROOT = Path(__file__).resolve().parents[1]


def test_short_recruiter_readme_preserves_required_evidence():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    archive = (ROOT / "docs/ENGINEERING_REFERENCE.md").read_text(
        encoding="utf-8")
    assert len(readme.splitlines()) < 200
    assert "docs/ENGINEERING_REFERENCE.md" in readme
    assert "docs/REPRODUCIBILITY.md" in readme
    assert "docs/GITHUB_ABOUT.md" in readme
    assert "## Dashboard design and activity signals" in archive
    assert "## P0 verified-first portfolio" in archive
    for path in ("src/ui/dashboard_v2.py", "scripts/sql_insights.py",
                 "docs/EVIDENCE_CASE_STUDIES.md", "docs/gallery/mobile.jpg"):
        assert path in readme
    assert "75-repository figures describe archived experiments" in readme


def test_archived_local_links_have_correct_relative_paths():
    archive = (ROOT / "docs/ENGINEERING_REFERENCE.md").read_text(
        encoding="utf-8")
    import re
    for link in re.findall(r"\]\(([^)]+)\)", archive):
        if link.startswith(("http:", "https:", "#", "mailto:")):
            continue
        relative = link.split("#", 1)[0]
        if relative:
            assert (ROOT / "docs" / relative).exists(), link


def test_recorded_environment_is_measured_not_hardcoded():
    required = "streamlit>=1.42,<2\npandas>=2.2,<3\n"
    versions = {"streamlit": "1.50.2", "pandas": "2.3.2"}
    r = make_receipt(required, versions=versions.__getitem__,
                     python_version="3.12.10", source_commit="abc",
                     generated_at="2026-11-14T00:00:00+00:00")
    assert r["direct_dependency_versions"] == versions
    assert r["python_version"] == "3.12.10"
    assert r["source_commit"] == "abc"
    assert "NOT a dependency lock" in r["audit_type"]
    assert len(r["requirements_sha256"]) == 64


def test_missing_dependency_not_pretended_installed():
    def missing(name):
        raise metadata.PackageNotFoundError(name)
    with pytest.raises(RuntimeError, match="Missing installed dependency"):
        make_receipt("fake-package>=99\n", versions=missing)
