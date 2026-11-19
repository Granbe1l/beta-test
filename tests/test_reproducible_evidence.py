from datetime import timedelta
from pathlib import Path
import pytest
from scripts import audit_reviewer_evidence as audit_module
from src.analytics.snapshot import read_snapshot


def test_old_snapshot_reproducible_audit_is_explicit_and_operational_gate_stays_strict():
    _, _, meta = read_snapshot()
    later = meta['generated_at'] + timedelta(days=30)
    proof = audit_module.audit(reproducible=True, now=later)
    assert proof['status'] == 'passed'
    assert proof['evaluation_mode'] == 'reproducible_at_capture'
    assert proof['evaluated_as_of_utc'] == meta['generated_at'].isoformat()
    assert proof['operational_freshness_verified'] is False
    assert proof['evidence_backed_findings'] > 0
    with pytest.raises(AssertionError, match='fresh|verified cohort'):
        audit_module.audit(now=later)


def test_workflows_separate_reproducible_and_operational_evidence():
    root = Path(__file__).resolve().parents[1]
    quality = (root/'.github/workflows/ci.yml').read_text()
    publisher = (root/'.github/workflows/public-snapshot.yml').read_text()
    assert 'python scripts/audit_reviewer_evidence.py --reproducible' in quality
    assert 'python scripts/audit_reviewer_evidence.py --require-fresh' in publisher
    assert '--reproducible' not in publisher
