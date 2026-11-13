from datetime import datetime,timedelta,timezone
from src.analytics.metrics import ratio, calculate_issues,calculate_prs,calculate_ci,closure_change,comparable_metrics
from src.analytics.findings import findings_for_repo
from src.analytics.read import load_reports,available_source
from src.database.models import SyncCheckpoint
from .conftest import NOW


def test_denominator_zero():
    assert ratio(1,0) is None
    assert ratio(3,4)==75.0


def test_issue_aging_and_trends():
    items=[{"state":"open","created_at":NOW-timedelta(days=d),"closed_at":None,"labels":["bug"]} for d in (3,10,50,100)]
    m=calculate_issues(items,NOW,90,True,NOW-timedelta(days=180))
    assert m["observed_open"] == 4
    assert m["sample_aged_open"] == 2 and m["sample_aged_percent"] == 50.0
    assert m["aged_open"] is None and m["aged_percent"] is None
    assert sum(row["count"] for row in m["weekly_opened"]) == 3
    verified = calculate_issues(items, NOW, 90, True, NOW-timedelta(days=180),
                                 backlog_complete=True)
    assert verified["aged_open"] == 2 and verified["aged_percent"] == 50.0
    partial=calculate_issues(items,NOW,90,False,NOW-timedelta(days=180))
    assert partial["aged_percent"] is None and partial["weekly_opened"] is None
    assert partial["sample_aged_percent"] == 50.0


def test_pr_median_vs_mean_and_draft():
    durations=[1,2,3,4,80]
    prs=[{"state":"closed","draft":False,"created_at":NOW-timedelta(days=d+1),"merged_at":NOW-timedelta(days=1),"closed_at":NOW-timedelta(days=1)} for d in durations]
    prs.append({"state":"open","draft":True,"created_at":NOW-timedelta(days=2),"merged_at":None,"closed_at":None})
    m=calculate_prs(prs,NOW,90,True,NOW-timedelta(days=180))
    assert m["open"]==1 and m["draft_open"]==1
    assert m["median_merge_days"]==3.0 and m["median_merge_days"] != sum(durations)/5


def test_ci_completed_known_denominator():
    rows=[{"created_at":NOW-timedelta(days=1),"status":"completed","conclusion":c} for c in ("success","success","failure","skipped",None)]
    rows.append({"created_at":NOW-timedelta(days=1),"status":"in_progress","conclusion":None})
    m=calculate_ci(rows,NOW,90,True,NOW-timedelta(days=180))
    assert m["completed"]==5 and m["success"]==2 and m["known_conclusion_denominator"]==4
    assert m["success_percent"]==50


def test_closure_comparison():
    items=[{"closed_at":NOW-timedelta(days=3)} for _ in range(8)]+[{"closed_at":NOW-timedelta(days=37)} for _ in range(5)]
    c=closure_change(items,NOW,True,NOW-timedelta(days=180))
    assert c["recent"]==8 and c["previous"]==5 and c["change_percent"]==60
    assert closure_change(items,NOW,False,None) is None


def test_stale_not_zeros():
    cp=SyncCheckpoint(repo_id=1,source="issues",status="complete",last_success_at=NOW-timedelta(hours=13))
    assert available_source(cp,NOW,12)=="stale"
    cp.status="failed"
    assert available_source(cp,NOW,12)=="failed"
    assert available_source(None,NOW,12)=="unavailable"


def test_cross_repository_suppresses_low_sample():
    r={"repository":{"full_name":"org/repo","category":"Web applications","language":"TypeScript"},
       "issues":{"aged_percent":90,"aged_denominator":2},
       "prs":{"median_merge_days":None,"merge_duration_n":3},
       "closure":None,"coverage_ok":True}
    result=comparable_metrics([r])[0]
    assert result["30+ day issues (%)"] is None and result["Median merge (days)"] is None


def test_finding_requires_evidence():
    r={"repository":{"full_name":"org/repo","url":"https://github.com/org/repo"},
       "issues":{"aged_denominator":10,"aged_percent":70,"aged_open":7},
       "prs":{"median_merge_days":None,"merge_duration_n":0,"merged_evidence":[]},
       "ci":{"known_conclusion_denominator":None,"success_percent":None},"closure":None}
    f=findings_for_repo(r)[0]
    assert "70%" in f["headline"] and "7 of 10" in f["evidence"] and f["url"].startswith("https://github.com/")
