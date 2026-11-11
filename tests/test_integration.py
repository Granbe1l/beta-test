"""Offline end-to-end integration against deterministic fixtures (NOT live GitHub)."""
from dataclasses import replace
from datetime import timedelta
from src.collectors.sync import synchronize
from src.analytics.read import load_reports
from src.analytics.findings import portfolio_findings
from src.database.models import Repository
from .conftest import NOW,issue_payload,pr_payload,run_payload


class Page:
    def __init__(self,items):self.items=items;self.pages=1;self.complete=True

class IntegrationClient:
    def paginate(self,path,params,max_pages,**kwargs):
        if path.endswith('/issues'):
            issues=[]
            for n in range(1,12):
                raw=issue_payload(n)
                raw['created_at']='2026-09-01T00:00:00Z'
                issues.append(raw)
            issues.append(issue_payload(50,is_pr=True))
            return Page(issues)
        if path.endswith('/pulls'):
            return Page([pr_payload(n) for n in range(1,7)])
        return Page([run_payload(n) for n in range(1,13)])


def test_offline_pipeline_produces_defensible_findings(db,cfg):
    with db.no_autoflush:
        rows=synchronize(db,IntegrationClient(),cfg,reconcile=True)
    assert len(rows)==3 and all(v['status']=='complete' for v in rows)
    # Sync runner timestamps are actual processing time; inspect using the same clock.
    reports=load_reports(db,observation_days=90,stale_hours=12)
    assert len(reports)==1
    r=reports[0]
    assert r['issues']['total_observed']==11
    assert r['prs']['total_observed']==6
    assert r['ci']['total_observed']==12
    assert r['issues']['observed_open']==11
    assert r['prs']['median_merge_days'] is not None
    findings=portfolio_findings(reports)
    assert any(f['type']=='issue-aging' for f in findings)
    assert all(f['url'].startswith('https://github.com/') for f in findings)
