"""Verify repo footprint warning policy without network or synthetic data claims."""
from scripts.repository_growth import evaluate


def test_report_below_warning_threshold_is_not_false_alarm():
    row = evaluate(112854, 1977914)
    assert row["approx_repo_size_mib"] == 110.21
    assert row["warning"] is False
    assert row["current_snapshot_bytes"] == 1977914
    assert "approximate" in row["measurement_limits"]


def test_warning_requires_threshold_crossing():
    assert evaluate(200 * 1024 - 1, 0)["warning"] is False
    assert evaluate(200 * 1024, 0)["warning"] is True


def test_invalid_size_rejected():
    from pytest import raises
    with raises(ValueError):
        evaluate(-1, 1)
    with raises(ValueError):
        evaluate(1, -1)
