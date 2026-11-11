"""Validate immutable GitHub snapshots without requiring live network."""
from datetime import timedelta
from pathlib import Path
from src.analytics.snapshot import export_snapshot, read_snapshot
from src.ui.charts import category_counts, observed_age_bands, observed_merge_times, source_coverage_counts
from .conftest import NOW

def test_snapshot_roundtrip_and_expiry(tmp_path):
    path=tmp_path/"snapshot.json.gz"
    coverage={s:{"status":"complete","last_success_at":NOW,"coverage_start":NOW-timedelta(days=180)}
              for s in ("issues","pull_requests","workflow_runs")}
    rows=[{"id":1,"repo_id":5,"number":1,"state":"open","created_at":NOW-timedelta(days=50),
           "updated_at":NOW,"closed_at":None,"url":"https://github.com/org/r/issues/1","labels":[]}]
    reports=[{"repository":{"id":5,"full_name":"org/r","category":"Data & backend","language":"Python"},
              "issue_rows":rows,"pr_rows":[],"ci_rows":[],"status":{},"coverage":coverage,
              "last_success":NOW,"coverage_ok":True}]
    audit={"candidates":1,"selected":1}
    result=export_snapshot(path,reports,audit,generated_at=NOW)
    assert result["source_records"]["issues"]==1
    loaded,selection,meta=read_snapshot(path,now=NOW)
    assert selection==audit and meta["mode"]=="snapshot"
    assert loaded[0]["issues"]["aged_percent"]==100.0
    assert loaded[0]["issue_rows"][0]["url"].startswith("https://github.com/")
    older,_,stale=read_snapshot(path,now=NOW+timedelta(hours=13))
    assert stale["stale"]
    assert older[0]["issues"]["aged_percent"] is None
    assert older[0]["status"]["issues"]=="stale"

def test_charts_use_only_real_rows():
    reports=[{"repository":{"category":"Cloud & infrastructure"},"status":{"issues":"partial","pull_requests":"complete","workflow_runs":"failed"}}]
    assert category_counts(reports)=={"Cloud & infrastructure":1}
    assert source_coverage_counts(reports)["partial"]==1
    assert sum(observed_age_bands([]).values())==0
    assert sum(observed_merge_times([]).values())==0
