"""Wait for the inspector result before capturing a genuine browser frame."""

from playwright.sync_api import TimeoutError as PlaywrightTimeout


def wait_for_inspection(page, *, timeout):
    heading = page.get_by_text(
        "What should the project manager inspect?", exact=True,
    )
    errors = page.locator('[data-testid="stAlertContentError"]:visible')
    heading.or_(errors).first.wait_for(timeout=timeout)
    if heading.is_visible():
        return

    message = errors.first.inner_text()
    if message != "GitHub could not be reached. Try again later.":
        raise AssertionError(f"Public inspector rejected the request: {message}")

    # Use the same bounded retry available to a visitor. A quota restriction
    # or invalid repository needs an operator, not another automated request.
    page.get_by_role("button", name="Refresh this inspection").click(timeout=timeout)
    try:
        heading.wait_for(timeout=timeout)
    except PlaywrightTimeout as exc:
        current_message = errors.first.inner_text() if errors.count() else message
        raise AssertionError(
            f"Public inspector did not recover after one refresh: {current_message}"
        ) from exc
