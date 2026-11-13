"""Read-only audit of true counts and complete source coverage."""
from pathlib import Path
import json, sys
from sqlalchemy import select, func
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.config.settings import Settings
from src.database.store import make_engine, session_factory
from src.database.models import Repository, Issue, PullRequest, WorkflowRun, SyncCheckpoint
from src.analytics.read import load_reports, selection_info
from src.analytics.findings import portfolio_findings


def main():
    cfg=Settings.from_env(); engine=make_engine(cfg.database_url)
    with session_factory(engine)() as session:
        reports=load_reports(session,observation_days=cfg.comparison_days,stale_hours=cfg.stale_hours)
        selection=selection_info(session)
        counts={name:session.scalar(select(func.count()).select_from(model)) for name,model in [("issues",Issue),("pull_requests",PullRequest),("workflow_runs",WorkflowRun)]}
        from collections import Counter
        from datetime import datetime, timezone, timedelta
        from src.analytics.metrics import utc
        now = datetime.now(timezone.utc)
        source_status = {}
        for source in ("issues", "pull_requests", "workflow_runs"):
            states = Counter(r["status"].get(source, "unavailable") for r in reports)
            ready28 = sum(
                r["status"].get(source) == "complete"
                and (cp := ((r.get("coverage") or {}).get(source) or {})).get("coverage_start")
                and utc(cp["coverage_start"]) <= now - timedelta(days=28)
                for r in reports)
            source_status[source] = {
                "complete": states["complete"], "partial": states["partial"],
                "stale": states["stale"], "failed": states["failed"],
                "unavailable": states["unavailable"],
                "verified_28d": ready28, "total_repositories": len(reports)}
        backlog = Counter(r.get("open_backlog_status", "unavailable") for r in reports)
        source_status["open_backlog"] = {
            "complete": backlog["complete"],
            "partial": backlog["partial"],
            "stale": backlog["stale"],
            "failed": backlog["failed"],
            "unavailable": backlog["unavailable"],
            "total_repositories": len(reports),
            "meaning": "independent full open-Issue scan, not verified 28-day event coverage",
        }
        print(json.dumps({"selection":({k:v for k,v in selection.items() if k!="decisions"} if selection else None),
                          "repositories":[{
                              "name":r["repository"]["full_name"],
                              "status":r["status"],
                              "open_backlog_status":r.get("open_backlog_status", "unavailable"),
                              "source_details":{
                                  source: {
                                      field: (r.get("coverage") or {}).get(source, {}).get(field)
                                      for field in ("status", "coverage_start",
                                                    "last_success_at", "pages_fetched",
                                                    "records_fetched", "last_error")
                                  } if (r.get("coverage") or {}).get(source) else {}
                                  for source in ("issues", "pull_requests",
                                                 "workflow_runs", "open_backlog")
                              },
                              "last_success_at":{
                                  source:((r.get("coverage") or {}).get(source) or {}).get("last_success_at")
                                  for source in ("issues","pull_requests","workflow_runs")},
                              "record_counts":{k:r[k]["total_observed"]
                                               for k in ("issues","prs","ci")}
                          } for r in reports],
                          "counts":counts,"coverage_summary":source_status,
                          "findings":portfolio_findings([r for r in reports if r["coverage_ok"]],5)},indent=2,default=str))
    engine.dispose()
if __name__=="__main__":main()
