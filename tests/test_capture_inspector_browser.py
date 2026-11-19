"""Browser checks for the screenshot runner's handling of inspector outcomes."""
import os

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("PDM_TEST_CAPTURE_BROWSER") != "1",
    reason="Requires the optional Playwright runtime and installed Chrome",
)

SUCCESS = "What should the project manager inspect?"
UNREACHABLE = "GitHub could not be reached. Try again later."
RESTRICTED = "GitHub API rate limit or access restriction. Retry after the limit resets."


@pytest.fixture
def page():
    from playwright.sync_api import Error, sync_playwright

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(channel="chrome", headless=True)
        except Error:
            browser = playwright.chromium.launch(headless=True)
        try:
            yield browser.new_page()
        finally:
            browser.close()


def show_rejected_inspection(page, message, retry_script):
    page.set_content(f"""
        <main id="result">
            <div data-testid="stAlertContentError">{message}</div>
            <button onclick="{retry_script}">Refresh this inspection</button>
        </main>
    """)


def test_temporary_transport_failure_retries_real_browser_once(page):
    from scripts.capture_inspector import wait_for_inspection

    show_rejected_inspection(
        page, UNREACHABLE,
        f"document.querySelector('#result').innerText = '{SUCCESS}'",
    )
    wait_for_inspection(page, timeout=1000)
    assert page.get_by_text(SUCCESS, exact=True).is_visible()


def test_restricted_inspection_fails_with_visible_reason_without_retry(page):
    from scripts.capture_inspector import wait_for_inspection

    show_rejected_inspection(page, RESTRICTED, "this.dataset.clicked = 'yes'")
    with pytest.raises(AssertionError, match="rate limit or access restriction"):
        wait_for_inspection(page, timeout=1000)
    assert page.get_by_role("button").get_attribute("data-clicked") is None


def test_persistent_transport_failure_reports_cause_after_one_retry(page):
    from scripts.capture_inspector import wait_for_inspection

    show_rejected_inspection(
        page, UNREACHABLE,
        "this.dataset.clicks = (+this.dataset.clicks || 0) + 1",
    )
    with pytest.raises(AssertionError, match="GitHub could not be reached"):
        wait_for_inspection(page, timeout=500)
    assert page.get_by_role("button").get_attribute("data-clicks") == "1"
