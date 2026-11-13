"""Verify a REAL public Streamlit deployment from a GitHub Actions runner.

This is intentionally separate from the local Playwright screenshot test:
localhost passing cannot establish public availability, fresh published
data, or a usable recruiter-facing demo.
"""
from __future__ import annotations

from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data" / "github_public_snapshot.json.gz"
ALLOWED_HOSTS = (".streamlit.app", ".onrender.com", ".up.railway.app")


def validate_public_app_url(url: str) -> str:
    """Strict host allow-list prevents user-supplied internal-network probes."""
    if not isinstance(url, str) or not url.strip():
        raise ValueError("Provide the deployed HTTPS Streamlit app URL")
    target = url.strip()
    parts = urlsplit(target)
    host = (parts.hostname or "").lower()
    if (parts.scheme != "https" or not host
            or parts.username or parts.password or parts.query or parts.fragment
            or parts.port not in (None, 443)
            or not any(host.endswith(suffix) for suffix in ALLOWED_HOSTS)):
        raise ValueError(
            "Use an HTTPS Streamlit/Render/Railway public app URL "
            "(not a private IP, preview token, or localhost)")
    return "https://" + host + parts.path.rstrip("/") + "/"


def expected_snapshot_stamp(path: Path = SNAPSHOT) -> str:
    """The exact visible timestamp from the repository's checked-in snapshot."""
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        payload = json.load(stream)
    if payload.get("schema_version") != 1 or len(payload.get("reports") or []) != 50:
        raise ValueError("Local repository snapshot does not contain 50 curated repository records")
    stamp = datetime.fromisoformat(payload["generated_at"].replace("Z", "+00:00"))
    stamp = stamp.astimezone(timezone.utc)
    return stamp.strftime("%d %b %Y · %H:%M UTC")


def verify_public_demo(url: str, snapshot_path: Path = SNAPSHOT,
                       screenshots_dir: Path | None = None) -> dict:
    """Check the actual remote UI, its charts, navigation and freshness."""
    from playwright.sync_api import sync_playwright
    public_url = validate_public_app_url(url)
    expected = expected_snapshot_stamp(snapshot_path)
    destination = screenshots_dir or ROOT / "docs" / "screenshots"
    destination.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 960})
            response = page.goto(public_url, wait_until="domcontentloaded", timeout=90_000)
            if response is None or response.status >= 400:
                raise RuntimeError("Public app returned an error or did not respond")
            page.locator(".d-hero").first.wait_for(timeout=120_000)
            page.get_by_role("button", name="Key findings").wait_for(timeout=20_000)
            body = page.locator("body").inner_text(timeout=20_000)
            if "PUBLIC GITHUB SNAPSHOT" not in body:
                raise AssertionError("Hosted app does not show the verified snapshot banner")
            if expected not in body:
                raise AssertionError(
                    f"Deployed snapshot differs from repository (expected {expected}). "
                    "Check Streamlit deployment/reboot before publishing this demo.")
            if page.locator('[data-testid="stPlotlyChart"]').count() < 1:
                raise AssertionError("Public Dashboard did not display an activity chart")
            if "Data source unavailable" in body or "No verified GitHub snapshot" in body:
                raise AssertionError("Public Dashboard reported a failed data source")
            page.screenshot(
                path=str(destination / "public-demo-overview.png"), full_page=False)
            page.get_by_role("button", name="Key findings").click(timeout=15_000)
            page.get_by_text("Priorities for a closer look").first.wait_for(
                timeout=60_000)
            page.screenshot(
                path=str(destination / "public-demo-findings.png"), full_page=False)
            return {
                "public_url": public_url,
                "expected_snapshot_utc": expected,
                "dashboard_chart_visible": True,
                "key_findings_page_visible": True,
                "repo_count": 50,
            }
        finally:
            browser.close()


def main() -> int:
    url = os.getenv("PUBLIC_APP_URL", "").strip()
    if not url:
        print(
            "PUBLIC DEPLOYMENT NOT VERIFIED: No app URL configured. "
            "Deploy the repository in Streamlit Community Cloud and set "
            "PUBLIC_APP_URL (Actions variable) or supply the workflow URL.",
            file=sys.stderr,
        )
        return 2
    try:
        evidence = verify_public_demo(url)
    except Exception as exc:
        print(f"PUBLIC DEMO VERIFICATION FAILED: {exc}", file=sys.stderr)
        return 1
    print("PUBLIC DEMO VERIFIED:", json.dumps(evidence, sort_keys=True))
    if (summary := os.getenv("GITHUB_STEP_SUMMARY")):
        with open(summary, "a", encoding="utf-8") as file:
            file.write("## Public Streamlit deployment check\n\n")
            for k, v in evidence.items():
                file.write(f"- **{k}:** {v}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
