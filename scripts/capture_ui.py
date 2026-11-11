"""Capture actual Streamlit browser renders; no synthetic data is inserted."""
from pathlib import Path
import os
import subprocess
import sys
import time
import requests
from playwright.sync_api import sync_playwright

OUT = Path("docs/screenshots")
OUT.mkdir(parents=True, exist_ok=True)
server = subprocess.Popen(
    [sys.executable, "-m", "streamlit", "run", "streamlit_app.py",
     "--server.port", "8501", "--server.address", "127.0.0.1",
     "--server.headless", "true", "--browser.gatherUsageStats", "false"],
    stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
    env={**os.environ, "STREAMLIT_SERVER_HEADLESS": "true"},
)
try:
    for _ in range(60):
        try:
            if requests.get("http://127.0.0.1:8501/_stcore/health", timeout=2).status_code == 200:
                break
        except requests.RequestException:
            pass
        time.sleep(1)
    else:
        raise RuntimeError("Streamlit did not become healthy")

    with sync_playwright() as pw:
        # GitHub Actions ubuntu-latest includes Chrome; run a real browser.
        try:
            browser = pw.chromium.launch(channel="chrome", headless=True,
                                         args=["--no-sandbox", "--disable-dev-shm-usage"])
        except Exception:
            browser = pw.chromium.launch(headless=True,
                                         args=["--no-sandbox", "--disable-dev-shm-usage"])

        desktop = browser.new_page(viewport={"width": 1440, "height": 960},
                                   device_scale_factor=1)
        desktop.goto("http://127.0.0.1:8501", wait_until="domcontentloaded")
        desktop.locator(".page-title").first.wait_for(timeout=45000)
        time.sleep(2)
        desktop.screenshot(path=str(OUT / "desktop-overview.png"), full_page=True)
        print("Captured desktop overview", flush=True)

        for label, file in [("Issues & backlog", "desktop-issues.png"),
                            ("Pull request review", "desktop-pull-requests.png"),
                            ("CI/CD activity", "desktop-ci-cd.png"),
                            ("Risks & recommendations", "desktop-findings.png")]:
            desktop.get_by_text(label, exact=False).first.click(timeout=10000)
            time.sleep(1.5)
            desktop.screenshot(path=str(OUT / file), full_page=True)
            print("Captured " + file, flush=True)

        mobile = browser.new_page(viewport={"width": 390, "height": 844},
                                  device_scale_factor=1, is_mobile=True,
                                  has_touch=True)
        mobile.goto("http://127.0.0.1:8501", wait_until="domcontentloaded")
        mobile.locator(".page-title").first.wait_for(timeout=45000)
        time.sleep(2)
        # On narrow screens Streamlit may start with the sidebar drawer open.
        # Save navigation separately, then close it using Streamlit's own control.
        mobile.screenshot(path=str(OUT / "mobile-navigation.png"), full_page=True)
        collapse = mobile.locator('[data-testid="stSidebarCollapseButton"]')
        if collapse.count() and collapse.first.is_visible():
            collapse.first.click(timeout=8000)
            time.sleep(1.5)
        mobile.screenshot(path=str(OUT / "mobile-overview.png"), full_page=True)
        print("Captured mobile navigation and overview", flush=True)
        browser.close()
finally:
    server.terminate()
    try: server.wait(timeout=10)
    except subprocess.TimeoutExpired: server.kill()
