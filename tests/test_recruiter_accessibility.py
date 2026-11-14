"""Scoped readability regression: objective palette contrast, not a human usability claim.

WCAG 2.2 normal-size text target is 4.5:1. This tests known CSS
foreground/background pairs; it is not a complete WCAG conformance audit.
"""
from src.ui.theme_v2 import CSS_V2


def contrast(foreground: str, background: str) -> float:
    def luminance(color):
        channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [v / 12.92 if v <= 0.04045 else
                  ((v + 0.055) / 1.055) ** 2.4 for v in channels]
        return sum(x * weight for x, weight in zip(
            linear, (0.2126, 0.7152, 0.0722)))

    high, low = sorted([luminance(foreground), luminance(background)],
                       reverse=True)
    return (high + 0.05) / (low + 0.05)


def test_recruiter_facing_supporting_text_contrast():
    pairs = {
        "body muted text": ("#706A7E", "#F7F7FB"),
        "KPI note": ("#62556F", "#FFFFFF"),
        "chart explanatory note": ("#62556F", "#FFFFFF"),
        "review caveat": ("#594c6b", "#f4f0fb"),
        "source link": ("#563590", "#F4F0FA"),
        "sidebar navigation": ("#D9D1E7", "#241936"),
        "verified status": ("#14764E", "#E7F5EE"),
    }
    for label, (foreground, background) in pairs.items():
        assert foreground in CSS_V2, label
        assert background in CSS_V2 or (background == "#FFFFFF" and "background:#fff" in CSS_V2), label
        assert contrast(foreground, background) >= 4.5, label


def test_mobile_recruiter_copy_is_not_shrunk_to_unreadable_size():
    # Test precisely the visible supporting copy, not all third-party
    # Streamlit/Plotly elements. The Playwright audit covers rendered views.
    import re
    # Examine the last (most specific mobile) override rather than
    # hard-coding one exact font size: improvements must not fail this test.
    for selector, minimum_rem in (
        (".d-kpi-note", 0.74),
        (".d-kpi-label", 0.74),
        (".d-chart-sub", 0.74),
        (".d-hero-overview p", 0.75),
    ):
        pattern = re.escape(selector) + r"\{font-size:([0-9.]+)rem!important;"
        matches = re.findall(pattern, CSS_V2)
        assert matches, selector
        assert float(matches[-1]) >= minimum_rem, selector
    assert "color:#8C8499" not in CSS_V2
    assert "color:#827B90" not in CSS_V2
