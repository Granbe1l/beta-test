"""Gallery provenance and safety tests, using isolated test-only image fixtures.

Fixture images never enter the public GitHub data or the published gallery.
Production screenshots must come from successful Playwright browser capture.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

import pytest

from scripts.prepare_gallery import generate_gallery, IMAGES


def _make_fixture_capture(tmp_path):
    Image = pytest.importorskip("PIL.Image")
    source = tmp_path / "browser"
    source.mkdir()
    for key, filename in IMAGES.items():
        dim = (390, 844) if key == "mobile" else (1440, 960)
        Image.new("RGB", dim, (242, 240, 247)).save(source / filename)
    (source / "recruiter-browser-audit.json").write_text(
        json.dumps({
            "desktop": {"rendered_plotly_charts": 3},
            "mobile_page_count": 6,
            "mobile_pages_tested": [
                "Dashboard", "Explore repositories", "Open issues",
                "Changes & reviews", "Build activity", "Key findings",
            ],
        }), encoding="utf-8")
    return source


def test_gallery_requires_proven_all_page_browser_audit(tmp_path):
    source = _make_fixture_capture(tmp_path)
    target = tmp_path / "gallery"
    audit = source / "recruiter-browser-audit.json"
    audit.unlink()
    with pytest.raises(FileNotFoundError):
        generate_gallery(source, target)
    audit.write_text(json.dumps({
        "desktop": {"rendered_plotly_charts": 3},
        "mobile_page_count": 1,
        "mobile_pages_tested": ["Dashboard"],
    }), encoding="utf-8")
    with pytest.raises(AssertionError):
        generate_gallery(source, target)


def test_gallery_has_seven_exact_provenance_matched_images(tmp_path, monkeypatch):
    source = _make_fixture_capture(tmp_path)
    target = tmp_path / "gallery"
    monkeypatch.setenv("GITHUB_SHA", "a"*40)
    manifest = generate_gallery(source, target)
    assert manifest["source_commit"] == "a"*40
    assert manifest["mobile_views_tested"] == 6
    assert len(manifest["screenshots"]) == 7
    for item in manifest["screenshots"]:
        assert (target/item["preview"]).stat().st_size > 0
        assert item["original_sha256"] == hashlib.sha256(
            (source/item["original"]).read_bytes()).hexdigest()
    assert (target/"manifest.json").is_file()


def test_missing_original_screenshot_is_hard_failure(tmp_path):
    source = _make_fixture_capture(tmp_path)
    (source / "desktop-issues.png").unlink()
    with pytest.raises(FileNotFoundError, match="desktop-issues.png"):
        generate_gallery(source, tmp_path / "gallery")


def test_workflow_does_not_write_to_repo_from_pull_requests():
    root = Path(__file__).resolve().parents[1]
    yaml = (root/".github/workflows/ui-screenshots.yml").read_text()
    assert "contents: read" in yaml
    assert "needs: screenshot" in yaml
    assert "github.event_name == 'push'" in yaml
    assert "github.ref == 'refs/heads/main'" in yaml
    assert "needs.screenshot.result == 'success'" in yaml
    assert "contents: write" in yaml
    assert "git add docs/gallery/*.jpg docs/gallery/manifest.json" in yaml
    # Previously a binary JPEG rebase could conflict after other UI merges.
    assert "git pull --rebase origin main" not in yaml
    assert "git reset --hard origin/main" in yaml
    assert "for attempt in 1 2 3" in yaml
    assert 'git diff --name-only "$GITHUB_SHA" origin/main' in yaml
    assert 'captured_in_ci_at_utc' in yaml
    assert "cp /tmp/verified-gallery/*.jpg" in yaml
    readme = (root/"README.md").read_text()
    for short_name in IMAGES:
        assert f"docs/gallery/{short_name}.jpg" in readme
