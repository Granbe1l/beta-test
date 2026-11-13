"""Deployment checks must distinguish a public URL from a local preview."""
from datetime import datetime, timezone
import gzip
import json

import pytest

from scripts.verify_public_demo import (
    validate_public_app_url, expected_snapshot_stamp,
)


@pytest.mark.parametrize("url,normalized", [
    ("https://example.streamlit.app", "https://example.streamlit.app/"),
    ("https://my-demo.onrender.com/", "https://my-demo.onrender.com/"),
    ("https://my-demo.up.railway.app", "https://my-demo.up.railway.app/"),
])
def test_only_known_public_streamlit_hosting(url, normalized):
    assert validate_public_app_url(url) == normalized


@pytest.mark.parametrize("url", [
    "",
    "http://example.streamlit.app/",
    "https://localhost:8501",
    "https://127.0.0.1",
    "https://192.168.1.2",
    "https://example.com",
    "https://streamlit.app.evil-site.example",
    "https://example.streamlit.app/?token=secret",
    "https://a:b@example.streamlit.app",
])
def test_reject_local_private_unknown_and_token_urls(url):
    with pytest.raises(ValueError):
        validate_public_app_url(url)


def test_production_timestamp_comes_from_actual_snapshot(tmp_path):
    path = tmp_path / "sample.json.gz"
    payload = {
        "schema_version": 1,
        "generated_at": datetime(2026, 11, 13, 4, 15, tzinfo=timezone.utc).isoformat(),
        "reports": [{}] * 75,
    }
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(payload, f)
    assert expected_snapshot_stamp(path) == "13 Nov 2026 · 04:15 UTC"
    payload["reports"] = [{}] * 74
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(payload, f)
    with pytest.raises(ValueError, match="75"):
        expected_snapshot_stamp(path)
