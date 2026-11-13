"""Date-field decoding must be bit-for-bit equivalent to the original path."""
from datetime import datetime, timezone
import json

from src.analytics.snapshot import _decode_json_object, decode, DATE_FIELDS


def test_single_pass_object_hook_keeps_all_nested_utc_timestamps_and_values():
    nested = {
        "schema_version": 1,
        "generated_at": "2026-11-13T12:00:00+00:00",
        "source": "Public GitHub REST API",
        "reports": [
            {
                "repository": {
                    "name": "sample",
                    "created_at": "2026-10-01T00:00:00Z",
                    "pushed_at": "2026-11-13T11:00:00+00:00",
                },
                "issue_rows": [
                    {"number": 1, "title": "Real title",
                     "created_at": "2026-11-12T00:00:00Z",
                     "closed_at": None, "labels": ["bug", "source"]},
                ],
                "coverage": {
                    "issues": {
                        "coverage_start": "2026-10-01T00:00:00Z",
                        "last_success_at": "2026-11-13T11:30:00Z",
                    }
                },
                "observations": [
                    {"measured_at": "2026-11-12T07:30:00Z",
                     "open_issues_observed": 0},
                ],
            }
        ],
    }
    raw = json.dumps(nested)
    old = decode(json.loads(raw))
    optimized = json.loads(raw, object_hook=_decode_json_object)
    assert optimized == old
    assert isinstance(optimized["reports"][0]["repository"]["created_at"], datetime)
    assert optimized["reports"][0]["issue_rows"][0]["closed_at"] is None
    assert optimized["reports"][0]["issue_rows"][0]["labels"] == ["bug", "source"]
    assert optimized["generated_at"] == nested["generated_at"]


def test_date_fields_are_scoped_only_to_known_keys():
    row = {
        "created_at": "2026-11-13T00:00:00Z",
        "closed_at": None,
        "description": "2026-11-13T00:00:00Z",
        "other": {"updated_at": "2026-11-12T00:00:00Z"},
    }
    parsed = json.loads(json.dumps(row), object_hook=_decode_json_object)
    assert parsed["description"] == row["description"]
    assert parsed["created_at"].tzinfo == timezone.utc
    assert parsed["other"]["updated_at"].tzinfo == timezone.utc
    assert "description" not in DATE_FIELDS
