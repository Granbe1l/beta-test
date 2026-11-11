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
        print(json.dumps({"selection":({k:v for k,v in selection.items() if k!="decisions"} if selection else None),
                          "repositories":[{"name":r["repository"]["full_name"],"status":r["status"],"record_counts":{k:r[k]["total_observed"] for k in ("issues","prs","ci")}} for r in reports],
                          "counts":counts,"findings":portfolio_findings([r for r in reports if r["coverage_ok"]],5)},indent=2,default=str))
    engine.dispose()
if __name__=="__main__":main()
