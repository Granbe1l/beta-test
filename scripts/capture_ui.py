"""Capture actual Streamlit browser renders; no synthetic data is inserted."""
from pathlib import Path
import json
from io import BytesIO
import os
from PIL import Image
import subprocess
import sys
import time
import requests
from playwright.sync_api import sync_playwright

def assert_no_streamlit_exception(page, screen: str) -> None:
    """An attractive screenshot cannot hide a partially failed Streamlit page."""
    errors = page.locator('[data-testid="stException"]')
    if errors.count():
        messages = errors.all_text_contents()
        raise AssertionError(
            f"{screen}: rendered Streamlit exception(s): {messages[:3]}")
    

def reviewer_browser_metrics(page, device: str) -> dict:
    """Observe a genuine rendered viewport; do not simulate human comprehension."""
    result = page.evaluate("""() => ({
      viewport_px: window.innerWidth,
      document_px: document.documentElement.scrollWidth,
      rendered_kpi_cards: document.querySelectorAll('.d-kpi').length,
      rendered_plotly_charts: document.querySelectorAll('[data-testid="stPlotlyChart"]').length,
      has_public_source_notice: document.body.innerText.includes('PUBLIC GITHUB SNAPSHOT'),
      has_evidence_scope: document.body.innerText.includes('ANALYSIS COHORT:'),
      has_reviewer_question: document.body.innerText.includes('What should we inspect?')
    })""")
    result["device"] = device
    assert result["document_px"] <= result["viewport_px"] + 8, (
        f"{device}: horizontal page overflow: {result}")
    assert result["rendered_kpi_cards"] == 4, (
        f"{device}: four evidence cards must be rendered: {result}")
    assert result["rendered_plotly_charts"] >= 1, (
        f"{device}: dashboard must render genuine charts: {result}")
    assert result["has_public_source_notice"] and result["has_evidence_scope"], (
        f"{device}: source timestamp/scope must be visible: {result}")
    assert result["has_reviewer_question"], (
        f"{device}: decision prompt is not visible: {result}")
    print("Non-human browser viewport audit:", json.dumps(result, sort_keys=True),
          flush=True)
    return result


def capture_scrolling_main(page, path: Path, limit=17):
    """Capture the *scrollable Streamlit main*, not browser full_page=True.

    Streamlit scrolls in an internal container. Playwright full_page=True
    captures only its visible viewport and can falsely imply that charts
    below the fold are missing. This stitches real scroll positions and
    excludes the persistent sidebar on desktop.
    """
    node = page.evaluate("""() => {
        const options = [
          document.querySelector('[data-testid="stMain"]'),
          document.querySelector('section.main'),
          document.querySelector('[data-testid="stAppViewContainer"]'),
          document.scrollingElement,
        ].filter(Boolean);
        const matched = options.filter(el => (
          el.scrollHeight > el.clientHeight + 170 &&
          el.clientHeight >= Math.min(450, window.innerHeight * 0.5)));
        matched.sort((a,b) =>
          (b.scrollHeight - b.clientHeight) - (a.scrollHeight - a.clientHeight));
        window.__captureMainScroll = matched[0] || document.scrollingElement;
        return {
          available: Boolean(window.__captureMainScroll),
          span: (window.__captureMainScroll?.scrollHeight || 0) -
                (window.__captureMainScroll?.clientHeight || 0),
          height: window.__captureMainScroll?.scrollHeight || 0
        };
    }""")
    viewport = page.viewport_size
    w, h = viewport["width"], viewport["height"]
    x0 = 300 if w >= 1000 else 0
    top_padding = 55
    scroll_span = max(0, int(node["span"]))
    step = h - top_padding
    positions = list(range(0, scroll_span, step)) + [scroll_span]
    positions = sorted(set(positions))
    if len(positions) > limit:
        # A deterministic, bounded number of scroll segments. Always include
        # the bottom and avoid hiding the last charts.
        positions = [round(scroll_span * i / (limit - 1))
                     for i in range(limit)]
    img = Image.new("RGB", (w - x0, scroll_span + h), "#F7F7FB")
    seen = set()
    for i, value in enumerate(positions):
        current = page.evaluate("""(top) => {
          window.__captureMainScroll.scrollTop = top;
          return window.__captureMainScroll.scrollTop;
        }""", value)
        current = round(current)
        if current in seen:
            continue
        seen.add(current)
        page.wait_for_timeout(300)
        shot = Image.open(BytesIO(page.screenshot(full_page=False))).convert("RGB")
        cut = 0 if i == 0 else top_padding
        img.paste(shot.crop((x0, cut, w, h)), (0, current + cut))
    page.evaluate("() => {window.__captureMainScroll.scrollTop = 0}")
    img.save(path, optimize=True)
    assert path.stat().st_size > 10_000
    print(f"Captured full scrollable view: {path.name} "
          f"({img.width}×{img.height}px; {len(seen)} viewports)", flush=True)


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
        desktop_started = time.perf_counter()
        desktop.goto("http://127.0.0.1:8501", wait_until="domcontentloaded")
        desktop.locator(".d-hero").first.wait_for(timeout=45000)
        # Actual rendered reviewer summary must remain visible on desktop.
        desktop.get_by_text("What should we inspect?", exact=True).wait_for(timeout=30000)
        desktop.get_by_text("How complete is the evidence?", exact=True).wait_for(timeout=30000)
        desktop.locator('[data-testid="stPlotlyChart"]').first.wait_for(
            timeout=45000)
        desktop_initial_chart_ms = round(
            (time.perf_counter() - desktop_started) * 1000)
        time.sleep(2)
        assert_no_streamlit_exception(desktop, "Dashboard")
        browser_audit = {"desktop": reviewer_browser_metrics(desktop, "desktop")}
        browser_audit["desktop"]["local_first_chart_ms"] = desktop_initial_chart_ms
        browser_audit["desktop"]["timing_scope"] = (
            "local GitHub Actions Chrome/Streamlit only, not hosted Cloud"
        )
        desktop.screenshot(path=str(OUT / "desktop-overview.png"), full_page=True)
        desktop.get_by_text("Reading guide · 1 minute", exact=True).first.click(
            timeout=10000)
        desktop.get_by_text(
            "Uncollected or stale records cannot be counted as zero activity.",
            exact=False).first.wait_for(timeout=10000)
        desktop.screenshot(path=str(OUT / "desktop-reader-guide.png"),
                           full_page=False)
        desktop.get_by_text("Reading guide · 1 minute", exact=True).first.click(
            timeout=10000)
        print("Validated plain-language reviewer glossary in the real browser",
              flush=True)
        # A valid dashboard can have no qualifying findings. In that case
        # require the explicit empty-state explanation instead of a fake
        # source link. When a finding exists, check its *rendered text* rather
        # than assuming Streamlit's styled link has a fixed accessibility role.
        empty_review = desktop.get_by_text(
            "No source-backed finding passes the review thresholds.", exact=False)
        if empty_review.count():
            print("Reviewer evidence empty state is explicitly disclosed", flush=True)
        else:
            desktop.get_by_text(
                "Open an original GitHub record", exact=True).first.wait_for(
                    timeout=30000)
            print("Verified original GitHub evidence action in reviewer summary", flush=True)
        print("Captured desktop overview", flush=True)
        checks = desktop.get_by_text(
            "02 / Inspect all evidence-backed checks", exact=True)
        checks.wait_for(timeout=10000)
        checks.click(timeout=10000)
        desktop.get_by_text("CHECK 1/", exact=False).first.wait_for(
            timeout=10000)
        checks.click(timeout=10000)
        print("Verified collapsed evidence details expand to original checks",
              flush=True)
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
        # The long supporting charts are deliberately lazy/closed by default.
        deep = desktop.get_by_text(
            "Show supporting charts and source details", exact=True)
        deep.click(timeout=12000)
        desktop.get_by_text(
            "04 / Matched snapshot change", exact=True).wait_for(timeout=15000)
        desktop.get_by_text("04 / Matched snapshot change", exact=True).scroll_into_view_if_needed(timeout=10000)
        time.sleep(1.0)
        desktop.screenshot(path=str(OUT / "desktop-charts.png"), full_page=False)
        desktop.get_by_text(
            "Show supporting charts and source details", exact=True).click(
                timeout=12000)
        desktop.get_by_text(
            "04 / Matched snapshot change", exact=True).wait_for(
                state="detached", timeout=15000)
        desktop.evaluate("window.scrollTo(0, 0)")
        print("Captured line charts for issues and pull requests", flush=True)
        # Verify the actual CSV control works, not just that it is visible.
        with desktop.expect_download(timeout=20000) as download_info:
            desktop.get_by_role("button", name="Export displayed events (CSV)").click(timeout=10000)
        download = download_info.value
        assert download.suggested_filename.endswith(".csv"), "Wrong export type"
        csv_path = OUT / "validated-activity-export.csv"
        download.save_as(csv_path)
        exported = csv_path.read_text(encoding="utf-8")
        assert "Date,Issues opened,Issues closed,PRs opened,PRs merged" in exported
        print("Validated daily event export in the real browser", flush=True)
        capture_scrolling_main(desktop, OUT / "desktop-dashboard-full.png")



        for label, file in [("Explore repositories", "desktop-repositories.png"),
                            ("Open issues", "desktop-issues.png"),
                            ("Changes & reviews", "desktop-pull-requests.png"),
                            ("Build activity", "desktop-ci-cd.png"),
                            ("Key findings", "desktop-findings.png")]:
            desktop.get_by_text(label, exact=False).first.click(timeout=10000)
            time.sleep(1.5)
            assert_no_streamlit_exception(desktop, label)
            # Navigation can preserve the previous page scroll and hover
            # tooltip. Every gallery preview must start at the actual heading.
            desktop.evaluate("""() => {
              window.scrollTo(0, 0);
              for (const selector of ['[data-testid="stMain"]',
                                      '[data-testid="stAppViewContainer"]',
                                      'section.main']) {
                const element = document.querySelector(selector);
                if (element) element.scrollTop = 0;
              }
            }""")
            # Streamlit navigation buttons can retain keyboard focus
            # after clicking, keeping their help tooltip visible even when
            # the pointer has moved away. Blur it without hiding real UI.
            desktop.evaluate("""() => {
              const focused = document.activeElement;
              if (focused && typeof focused.blur === 'function') focused.blur();
            }""")
            desktop.keyboard.press("Escape")
            desktop.mouse.move(1434, 48)
            desktop.wait_for_timeout(850)
            tooltip = desktop.locator(
                '[role="tooltip"]:visible, [data-testid="stTooltipContent"]:visible'
            )
            assert tooltip.count() == 0, (
                f"{label}: transient hover tooltip remained over gallery capture"
            )
            desktop.screenshot(path=str(OUT / file), full_page=False)
            capture_scrolling_main(
                desktop, OUT / file.replace(".png", "-full.png"))
            print("Captured " + file, flush=True)
            if label == "Key findings":
                desktop.get_by_text(
                    "Real GitHub evidence walkthroughs", exact=True).wait_for(
                    timeout=15000)
                case_categories = [
                    ("Older open work", "/issues/"),
                    ("Automated check results", "/actions/runs/"),
                    ("Time to merge code changes", "/pull/"),
                ]
                inspected = []
                for case_name, expected_path in case_categories:
                    case_tab = desktop.get_by_role("tab", name=case_name)
                    if not case_tab.count():
                        # The real dataset may legitimately provide fewer than
                        # three examples; do not insert a simulated case.
                        continue
                    case_tab.first.click(timeout=10000)
                    link = desktop.get_by_role(
                        "link", name="Open recorded GitHub evidence").first
                    link.wait_for(timeout=10000)
                    href = link.get_attribute("href") or ""
                    assert (href.startswith("https://github.com/")
                            and expected_path in href), (
                        f"{case_name}: wrong individual source: {href}")
                    if case_name == "Time to merge code changes":
                        desktop.get_by_text(
                            "Individual linked PR:", exact=False).first.wait_for(
                            timeout=12000)
                        desktop.get_by_text(
                            "not a representative median", exact=False
                        ).first.wait_for(timeout=12000)
                    if case_name == "Automated check results":
                        exp = desktop.get_by_text(
                            "Recorded workflow mix · 28 days", exact=True)
                        exp.click(timeout=12000)
                        desktop.get_by_text(
                            "completed checks with known conclusions",
                            exact=False).first.wait_for(timeout=12000)
                        exp.click(timeout=12000)
                    inspected.append(case_name)
                    print(f"Verified real source tab: {case_name} / {href}",
                          flush=True)
                if not inspected:
                    assert desktop.get_by_text(
                        "No original-record examples meet", exact=False).count(), (
                        "Missing source cases need an honest empty state")
                print("Verified all available source-backed case tabs",
                      len(inspected), flush=True)
                export_action = desktop.get_by_role(
                    "button", name="Export evidence review plan (CSV)")
                if export_action.count():
                    with desktop.expect_download(timeout=20000) as csv_info:
                        export_action.click(timeout=10000)
                    export = csv_info.value
                    assert export.suggested_filename.endswith(".csv")
                    saved = OUT / "validated-evidence-review.csv"
                    export.save_as(saved)
                    content = saved.read_text(encoding="utf-8-sig")
                    assert "Reason to inspect" in content
                    assert "Review step 3" in content
                    assert "GitHub link (record or listing)" in content
                    print("Validated source-grounded reviewer CSV export",
                          flush=True)
                else:
                    assert desktop.get_by_text(
                        "No evidence-backed findings", exact=False).count() > 0, (
                        "Reviewer findings missing without an empty state")
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
                # Capture real public repository inspector states. This is
                # a strictly read-only external GitHub REST API preview.
                # Never insert mocked responses to make the screenshot pass.
                desktop.get_by_text("Inspect public GitHub URL", exact=True).click(
                    timeout=10000)
                desktop.get_by_text(
                    "Inspect a public GitHub project", exact=True).wait_for(
                        timeout=12000)
                form_url = desktop.get_by_role(
                    "textbox", name="GitHub repository URL")
                assert form_url.input_value() == "", (
                    "Empty-state screenshot unexpectedly had a URL")
                assert_no_streamlit_exception(desktop, "Inspector / URL empty")
                desktop.screenshot(
                    path=str(OUT / "desktop-inspector-empty.png"),
                    full_page=False)
                capture_scrolling_main(
                    desktop, OUT / "desktop-inspector-empty-full.png")
                print("Captured actual empty public GitHub URL form",
                      flush=True)
                form_url.fill("https://github.com/psf/requests")
                desktop.screenshot(
                    path=str(OUT / "desktop-inspector-url-entered.png"),
                    full_page=False)
                desktop.get_by_role(
                    "button", name="Inspect public project").click(
                        timeout=12000)
                desktop.get_by_text(
                    "What should the project manager inspect?",
                    exact=True).wait_for(timeout=40000)
                desktop.get_by_text(
                    "External API observation:", exact=False).wait_for(
                        timeout=40000)
                assert_no_streamlit_exception(
                    desktop, "Inspector / URL submitted")
                assert desktop.get_by_text("psf/requests", exact=True).count() > 0, (
                    "Inspector did not display fetched public repo name")
                # Streamlit renders the lower tab controls after the
                # headline on some browser runs; wait for them rather than
                # treating a mid-render frame as missing source evidence.
                desktop.get_by_role("tab", name="Issues").wait_for(
                    state="attached", timeout=30000)
                desktop.screenshot(
                    path=str(OUT / "desktop-inspector-submitted.png"),
                    full_page=False)
                capture_scrolling_main(
                    desktop, OUT / "desktop-inspector-submitted-full.png")
                # The actual browser export must preserve sampled source
                # evidence and the explicitly external/NOT Verified scope.
                with desktop.expect_download(timeout=20000) as export_info:
                    desktop.get_by_role(
                        "button", name="Download this inspection (CSV)").click(
                            timeout=12000)
                inspection = export_info.value
                assert inspection.suggested_filename.endswith(".csv")
                csv_file = OUT / "validated-inspection.csv"
                inspection.save_as(csv_file)
                csv_text = csv_file.read_text(encoding="utf-8-sig")
                assert "psf/requests" in csv_text
                assert "NOT a member of the 50 curated/Verified projects" in csv_text
                assert "Observed at UTC" in csv_text
                print("Validated inspector CSV export from real GitHub response",
                      flush=True)
                print("Captured actual GitHub URL submission with source evidence",
                      flush=True)
                # Restore the audited tracked mode before running existing
                # side-by-side and source-tab browser regression checks.
                desktop.get_by_text("Tracked dataset", exact=True).click(
                    timeout=12000)
                desktop.get_by_role(
                    "tab", name="Activity history").wait_for(timeout=12000)
                # Assert the initial history tab is genuinely informative even
                # when only one independent inventory snapshot exists.
                desktop.get_by_role("tab", name="Activity history").click(timeout=12000)
                desktop.get_by_text("Current collected snapshot", exact=True).wait_for(
                    timeout=12000)
                assert_no_streamlit_exception(desktop, "Activity history")
                desktop.screenshot(
                    path=str(OUT / "desktop-repositories-history-current.png"),
                    full_page=False)
                # These are required interactions. Do not silently pass a
                # screenshot workflow when the comparison page breaks.
                tab = "Compare projects"
                desktop.get_by_role("tab", name=tab).click(timeout=12000)
                time.sleep(1.2)
                assert desktop.get_by_text("First project", exact=True).count() >= 1
                assert desktop.get_by_text("Second project", exact=True).count() >= 1
                assert desktop.locator('[data-testid="stDataFrame"]').count() >= 1, (
                    "Side-by-side project comparison table did not render")
                links = desktop.get_by_role("link", name="View original GitHub project")
                assert links.count() >= 2, "Both project source links must be available"
                desktop.screenshot(
                    path=str(OUT / "desktop-repositories-compare-two.png"),
                    full_page=False)
                print("Validated two-project comparison controls, table and links",
                      flush=True)
                for tab in ("Compare projects", "Source details"):
                    desktop.get_by_role("tab", name=tab).click(timeout=10000)
                    time.sleep(1)
                    assert_no_streamlit_exception(desktop, "Explorer / " + tab)
                    if tab == "Compare projects":
                        # One unified tab contains both two-project evidence
                        # links and the cohort-wide verified chart/fallback.
                        assert desktop.get_by_text(
                            "Compare two selected repositories", exact=True).count()
                        assert desktop.get_by_text(
                            "Compare verified metrics across projects", exact=True).count()
                        has_comparison = (
                            desktop.get_by_text("Showing", exact=False).count() > 0
                            or desktop.get_by_text(
                                "No comparison is inferred from missing data.",
                                exact=False).count() > 0
                        )
                        assert has_comparison, (
                            "No source-qualified chart or labelled fallback "
                            "in unified cross-project comparison")
                        peer = desktop.get_by_text(
                            "Within-category context · median and spread",
                            exact=True)
                        peer.click(timeout=10000)
                        desktop.get_by_text(
                            "Data eligibility by category", exact=True).wait_for(
                            timeout=12000)
                        assert_no_streamlit_exception(
                            desktop, "Explorer / peer eligibility")
                        peer.click(timeout=10000)
                        print("Verified real peer eligibility disclosure", flush=True)
                    desktop.screenshot(
                        path=str(OUT / (
                            "desktop-repositories-" + tab.lower().replace(" ", "-") + ".png")),
                        full_page=False)
                    print("Captured Explorer tab: " + tab, flush=True)


        mobile = browser.new_page(viewport={"width": 390, "height": 844},
                                  device_scale_factor=1, is_mobile=True,
                                  has_touch=True)
        mobile_started = time.perf_counter()
        mobile.goto("http://127.0.0.1:8501", wait_until="domcontentloaded")
        mobile.locator(".d-hero").first.wait_for(timeout=45000)
        mobile.get_by_text("How complete is the evidence?", exact=True).wait_for(timeout=30000)
        mobile.locator('[data-testid="stPlotlyChart"]').first.wait_for(
            timeout=45000)
        mobile_initial_chart_ms = round(
            (time.perf_counter() - mobile_started) * 1000)
        time.sleep(2)
        assert_no_streamlit_exception(mobile, "Mobile Dashboard")
        browser_audit["mobile"] = reviewer_browser_metrics(mobile, "mobile")
        browser_audit["mobile"]["local_first_chart_ms"] = mobile_initial_chart_ms
        browser_audit["mobile"]["timing_scope"] = (
            "local GitHub Actions Chrome/Streamlit only, not hosted Cloud"
        )
        (OUT / "recruiter-browser-audit.json").write_text(
            json.dumps(browser_audit, indent=2, sort_keys=True), encoding="utf-8")
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
        capture_scrolling_main(mobile, OUT / "mobile-dashboard-full.png")
        print("Captured mobile navigation and overview", flush=True)

        def open_mobile_drawer():
            if drawer_open():
                return
            controls = (
                '[data-testid="stSidebarCollapsedControl"] button',
                '[data-testid="collapsedControl"] button',
                'button[aria-label="Open sidebar"]',
                'button[aria-label="Expand sidebar"]',
            )
            for selector in controls:
                toggle = mobile.locator(selector)
                if toggle.count() and toggle.first.is_visible():
                    try:
                        toggle.first.click(timeout=6000, force=True)
                        mobile.wait_for_timeout(600)
                        if drawer_open():
                            return
                    except Exception:
                        pass
            mobile.mouse.click(32, 32)
            mobile.wait_for_timeout(700)
            assert drawer_open(), "Mobile sidebar did not reopen after page change"

        def close_mobile_drawer():
            if not drawer_open():
                return
            toggle = mobile.locator('[data-testid="stSidebarCollapseButton"]')
            if toggle.count() and toggle.first.is_visible():
                toggle.first.click(timeout=7000)
            else:
                mobile.mouse.click(365, 250)
            mobile.wait_for_timeout(700)
            assert not drawer_open(), "Mobile sidebar obscured the selected page"

        tested_mobile = ["Dashboard"]
        for name, filename in (
            ("Explore repositories", "mobile-repositories"),
            ("Open issues", "mobile-issues"),
            ("Changes & reviews", "mobile-pull-requests"),
            ("Build activity", "mobile-ci-cd"),
            ("Key findings", "mobile-findings"),
        ):
            open_mobile_drawer()
            sidebar.get_by_role("button", name=name).click(timeout=12000)
            mobile.wait_for_timeout(1600)
            close_mobile_drawer()
            # Validate the actual rendered page, not only successful navigation.
            mobile.locator(".d-heading").first.wait_for(timeout=30000)
            assert_no_streamlit_exception(mobile, "Mobile " + name)
            dimensions = mobile.evaluate("""() => ({
              viewport: window.innerWidth,
              document: document.documentElement.scrollWidth
            })""")
            assert dimensions["document"] <= dimensions["viewport"] + 8, (
                f"Mobile {name}: horizontal overflow: {dimensions}")
            tested_mobile.append(name)
            mobile.screenshot(
                path=str(OUT / f"{filename}.png"), full_page=False)
            capture_scrolling_main(
                mobile, OUT / f"{filename}-full.png")
            if name == "Explore repositories":
                # Browser-test the public URL Inspector on an actual mobile
                # viewport, not just the regular tracked-repository Explorer.
                mobile.get_by_text("Inspect public GitHub URL", exact=True).click(
                    timeout=15000)
                mobile.get_by_text(
                    "Inspect a public GitHub project", exact=True).wait_for(
                        timeout=15000)
                url = mobile.get_by_role("textbox", name="GitHub repository URL")
                assert url.input_value() == ""
                assert_no_streamlit_exception(mobile, "Mobile Inspector / empty")
                mobile.screenshot(
                    path=str(OUT / "mobile-inspector-empty.png"), full_page=False)
                url.fill("https://github.com/psf/requests")
                mobile.get_by_role(
                    "button", name="Inspect public project").click(timeout=15000)
                mobile.get_by_text(
                    "What should the project manager inspect?",
                    exact=True).wait_for(timeout=45000)
                mobile.get_by_text(
                    "External API observation:", exact=False).wait_for(
                        timeout=45000)
                assert mobile.get_by_text(
                    "psf/requests", exact=True).count() >= 1
                assert_no_streamlit_exception(mobile, "Mobile Inspector / submitted")
                size = mobile.evaluate("""() => ({
                    viewport: window.innerWidth,
                    document: document.documentElement.scrollWidth
                })""")
                assert size["document"] <= size["viewport"] + 8, (
                    f"Mobile URL inspector horizontal overflow: {size}")
                mobile.screenshot(
                    path=str(OUT / "mobile-inspector-submitted.png"),
                    full_page=False)
                capture_scrolling_main(
                    mobile, OUT / "mobile-inspector-submitted-full.png")
                print("Validated real mobile GitHub URL inspector", flush=True)
                mobile.get_by_text("Tracked dataset", exact=True).click(
                    timeout=12000)
                mobile.get_by_role(
                    "tab", name="Activity history").wait_for(timeout=15000)
                for tab, screenshot in (
                    ("Activity history", "mobile-repositories-history"),
                    ("Compare projects", "mobile-repositories-comparison"),
                    ("Source details", "mobile-repositories-source-details"),
                ):
                    mobile.get_by_role("tab", name=tab).click(timeout=12000)
                    mobile.wait_for_timeout(800)
                    assert_no_streamlit_exception(mobile, "Mobile Explorer / " + tab)
                    mobile.screenshot(path=str(OUT / f"{screenshot}.png"),
                                      full_page=False)
            print("Verified responsive mobile page: " + name, flush=True)

        assert len(tested_mobile) == 6
        browser_audit["mobile_pages_tested"] = tested_mobile
        browser_audit["mobile_page_count"] = len(tested_mobile)
        (OUT / "recruiter-browser-audit.json").write_text(
            json.dumps(browser_audit, indent=2, sort_keys=True), encoding="utf-8")
        browser.close()
finally:
    server.terminate()
    try: server.wait(timeout=10)
    except subprocess.TimeoutExpired: server.kill()
