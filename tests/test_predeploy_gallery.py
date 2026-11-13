"""Permanent, non-fabricated GitHub reviewer image gallery gates."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_gallery_is_real_browser_capture_with_limitations():
    readme = (ROOT/"README.md").read_text(encoding="utf-8")
    guide = (ROOT/"docs/gallery/README.md").read_text(encoding="utf-8")
    for filename in (
        "dashboard.jpg", "repositories.jpg", "issues.jpg",
        "pull-requests.jpg", "ci-cd.jpg", "findings.jpg", "mobile.jpg",
    ):
        assert f"docs/gallery/{filename}" in readme
    assert "Playwright screenshots" in readme
    assert "not UI mockups" in readme
    assert "do **not** prove public Streamlit hosting" in readme
    assert "point-in-time images" in guide
    assert "without a six-page mobile test" in guide


def test_preview_generator_requires_all_original_images_and_browser_audit():
    code = (ROOT/"scripts/prepare_gallery.py").read_text(encoding="utf-8")
    for file in (
        "desktop-overview.png", "desktop-repositories.png",
        "desktop-issues.png", "desktop-pull-requests.png",
        "desktop-ci-cd.png", "desktop-findings.png", "mobile-overview.png",
    ):
        assert file in code
    assert 'audit.get("mobile_page_count") == 6' in code
    assert "original_sha256" in code
    assert "Actual Playwright screenshots" in code
    assert "actual.thumbnail" in code


def test_only_trusted_main_gallery_job_has_write_permission():
    workflow = (ROOT/".github/workflows/ui-screenshots.yml").read_text()
    assert "  screenshot:" in workflow
    assert "  gallery:" in workflow
    before, after = workflow.split("  gallery:", 1)
    assert "permissions:\n  contents: read" in before
    assert "needs: screenshot" in after
    assert "github.event_name == 'push'" in after
    assert "github.ref == 'refs/heads/main'" in after
    assert "contents: write" in after
    assert "actions/download-artifact@v4" in after
    assert "scripts/prepare_gallery.py" in before and after
    assert "git add docs/gallery/*.jpg docs/gallery/manifest.json" in after
    assert "[skip ci]" in after
