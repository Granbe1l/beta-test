"""Publish compact previews of actual Playwright UI screenshots, never mockups.

The CI screenshot job already asserts a real snapshot, rendered charts and
that all six mobile screens have no visible Streamlit exceptions/overflow.
This script only scales those PNGs and writes accurate provenance metadata.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

CAPTURES = Path("docs/screenshots")
GALLERY = Path("docs/gallery")
IMAGES = {
    "dashboard": "desktop-overview.png",
    "repositories": "desktop-repositories.png",
    "issues": "desktop-issues.png",
    "pull-requests": "desktop-pull-requests.png",
    "ci-cd": "desktop-ci-cd.png",
    "findings": "desktop-findings.png",
    "mobile": "mobile-overview.png",
}


def generate_gallery(source: Path = CAPTURES, target: Path = GALLERY) -> dict:
    from PIL import Image  # installed in browser screenshot workflow
    audit_file = source / "recruiter-browser-audit.json"
    if not audit_file.exists():
        raise FileNotFoundError(
            "Missing actual Playwright browser audit; gallery cannot be published.")
    audit = json.loads(audit_file.read_text(encoding="utf-8"))
    assert audit.get("mobile_page_count") == 6, (
        "Do not publish previews until all six mobile views were tested.")
    assert audit.get("desktop", {}).get("rendered_plotly_charts", 0) >= 1
    target.mkdir(parents=True, exist_ok=True)
    details = []
    for short_name, filename in IMAGES.items():
        original = source / filename
        if not original.is_file():
            raise FileNotFoundError(f"Actual screenshot missing: {original}")
        raw = original.read_bytes()
        with Image.open(original) as image:
            image.load()
            assert image.width >= (1000 if short_name != "mobile" else 320)
            assert image.height >= 550
            actual = image.convert("RGB")
            actual.thumbnail((1000, 900), Image.Resampling.LANCZOS)
            destination = target / f"{short_name}.jpg"
            actual.save(destination, "JPEG", optimize=True, quality=82)
        details.append({
            "preview": destination.name, "original": filename,
            "original_sha256": hashlib.sha256(raw).hexdigest(),
            "preview_bytes": destination.stat().st_size,
        })
    manifest = {
        "source": "Actual Playwright screenshots from Streamlit app with checked-in real public GitHub snapshot",
        "not": "Synthetic UI, production deployment proof, or real HR participant result",
        "captured_in_ci_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": os.environ.get("GITHUB_SHA", "local, unverified commit"),
        "mobile_views_tested": audit["mobile_page_count"],
        "screenshots": details,
    }
    (target / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print("Verified portfolio image gallery:", json.dumps({
        "images": len(details), "mobile_views": audit["mobile_page_count"],
        "source_commit": manifest["source_commit"],
    }))
    return manifest


if __name__ == "__main__":
    generate_gallery()
