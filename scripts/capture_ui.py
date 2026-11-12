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
        desktop.locator(".d-hero").first.wait_for(timeout=45000)
        time.sleep(2)
        desktop.screenshot(path=str(OUT / "desktop-overview.png"), full_page=True)
        print("Captured desktop overview", flush=True)
        # Capture the real 28-day line chart, not only the hero or KPIs.
        # Scroll to the actual chart canvas, not just its title (which may
        # already be visible at the bottom of the viewport).
        desktop.locator('[data-testid="stPlotlyChart"]:visible').first.scroll_into_view_if_needed(timeout=10000)
        time.sleep(1.2)
        desktop.screenshot(path=str(OUT / "desktop-line-issues.png"), full_page=False)
        desktop.get_by_role("tab", name="Pull requests · code changes").click(timeout=10000)
        desktop.locator('[data-testid="stPlotlyChart"]:visible').first.scroll_into_view_if_needed(timeout=10000)
        time.sleep(1.1)
        desktop.screenshot(path=str(OUT / "desktop-line-prs.png"), full_page=False)
        desktop.get_by_role("tab", name="Issues · tasks & reports").click(timeout=10000)
        time.sleep(.8)
        desktop.get_by_text("03 / Compare change without sample bias", exact=True).scroll_into_view_if_needed(timeout=10000)
        time.sleep(1.0)
        desktop.screenshot(path=str(OUT / "desktop-charts.png"), full_page=False)
        desktop.evaluate("window.scrollTo(0, 0)")
        print("Captured line charts for issues and pull requests", flush=True)

        for label, file in [("Explore repositories", "desktop-repositories.png"),
                            ("Open issues", "desktop-issues.png"),
                            ("Changes & reviews", "desktop-pull-requests.png"),
                            ("Build activity", "desktop-ci-cd.png"),
                            ("Key findings", "desktop-findings.png")]:
            desktop.get_by_text(label, exact=False).first.click(timeout=10000)
            time.sleep(1.5)
            desktop.screenshot(path=str(OUT / file), full_page=True)
            print("Captured " + file, flush=True)
            # Capture the lower portions of each screen's scrollable main view.
            try:
                desktop.mouse.move(1000, 700)
                desktop.mouse.wheel(0, 1705)
                time.sleep(0.7)
                desktop.screenshot(path=str(OUT / file.replace(".png", "-lower.png")),
                                   full_page=False)
                desktop.mouse.wheel(0, -2500)
                time.sleep(0.4)
            except Exception as exc:
                print("Additional viewport unavailable: " + str(exc), flush=True)
            if label == "Explore repositories":
                for tab in ("Compare projects", "Source details"):
                    try:
                        desktop.get_by_role("tab", name=tab).click(timeout=10000)
                        time.sleep(1)
                        desktop.screenshot(path=str(OUT / (
                            "desktop-repositories-" + tab.lower().replace(" ", "-") + ".png"
                        )), full_page=False)
                        print("Captured Explorer tab: " + tab, flush=True)
                    except Exception as exc:
                        print("Explorer tab capture unavailable: " + str(exc), flush=True)

        mobile = browser.new_page(viewport={"width": 390, "height": 844},
                                  device_scale_factor=1, is_mobile=True,
                                  has_touch=True)
        mobile.goto("http://127.0.0.1:8501", wait_until="domcontentloaded")
        mobile.locator(".d-hero").first.wait_for(timeout=45000)
        time.sleep(2)
        # Validate the actual mobile drawer. Previously navigation.png was
        # captured while closed and looked identical to the overview.
        sidebar = mobile.locator('[data-testid="stSidebar"]')
        nav_button = sidebar.get_by_role("button", name="Dashboard")
        def drawer_open():
            bounds = sidebar.bounding_box()
            return bool(bounds and bounds["x"] >= -10 and nav_button.is_visible())

        if not drawer_open():
            opened = False
            for selector in (
                '[data-testid="stSidebarCollapsedControl"] button',
                '[data-testid="stSidebarCollapsedControl"]',
                '[data-testid="collapsedControl"] button',
                '[data-testid="collapsedControl"]',
                'button[aria-label="Open sidebar"]',
                'button[aria-label="Expand sidebar"]',
            ):
                control = mobile.locator(selector)
                if control.count() and control.first.is_visible():
                    try:
                        control.first.click(timeout=5000, force=True)
                        time.sleep(1.2)
                        if drawer_open():
                            opened = True
                            break
                    except Exception:
                        continue
            if not opened:
                # Streamlit 1.67 mobile can use a chevron control with no
                # stable test-id; interact with its actual visible position.
                print("Sidebar toggle using top-left mobile chevron", flush=True)
                mobile.mouse.click(32, 32)
                time.sleep(1.2)
                opened = drawer_open()
            if not opened:
                controls = mobile.evaluate("""() => [...document.querySelectorAll('button')]
                    .slice(0,25).map(b => ({html:b.outerHTML.slice(0,220),
                    x:b.getBoundingClientRect().x,y:b.getBoundingClientRect().y}))""")
                bounds = sidebar.bounding_box()
                print("Mobile sidebar bounds:", bounds, flush=True)
                print("Mobile button controls:", controls, flush=True)
                raise AssertionError("Mobile sidebar drawer did not open in the browser; do not publish unverified navigation.")
        assert drawer_open(), "Mobile sidebar must be visible for the navigation screenshot"
        nav_bytes = mobile.screenshot(path=str(OUT / "mobile-navigation.png"), full_page=False)

        collapse = mobile.locator('[data-testid="stSidebarCollapseButton"]')
        if collapse.count() and collapse.first.is_visible():
            collapse.first.click(timeout=8000)
            time.sleep(0.8)
        else:
            # Streamlit backdrop can also close the drawer after a click outside it.
            mobile.mouse.click(360, 250)
            time.sleep(0.8)
        assert not drawer_open(), "Mobile sidebar must be closed for the overview screenshot"
        overview_bytes = mobile.screenshot(path=str(OUT / "mobile-overview.png"), full_page=True)
        assert nav_bytes != overview_bytes, "Mobile drawer and overview captures must differ"
        print("Captured mobile navigation and overview", flush=True)
        browser.close()
finally:
    server.terminate()
    try: server.wait(timeout=10)
    except subprocess.TimeoutExpired: server.kill()
