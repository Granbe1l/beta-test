"""Real browser gallery must remove navigation-focus tooltip before capture."""
from pathlib import Path

def test_gallery_dismisses_focused_help_without_hiding_ui():
    code = (Path(__file__).resolve().parents[1] / "scripts/capture_ui.py").read_text()
    segment = code.split('for label, file in [("Explore repositories"', 1)[1].split(
        'if label == "Key findings":', 1
    )[0]
    assert "focused.blur()" in segment
    assert 'desktop.keyboard.press("Escape")' in segment
    assert 'desktop.wait_for_timeout(850)' in segment
    assert '[role="tooltip"]:visible' in segment
    assert 'assert tooltip.count() == 0' in segment
    assert segment.index('assert tooltip.count() == 0') < segment.index(
        'desktop.screenshot(path=str(OUT / file), full_page=False)')
    assert "display:none" not in segment
