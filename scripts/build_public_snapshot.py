"""Build a genuine GitHub evidence snapshot from the temporary ingestion database."""
from pathlib import Path
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.analytics.read import load_reports,selection_info
from src.analytics.snapshot import SNAPSHOT_PATH,export_snapshot
from src.config.settings import Settings
from src.database.store import make_engine,session_factory

def main():
    cfg=Settings.from_env()
    engine=make_engine(cfg.database_url)
    try:
        with session_factory(engine)() as session:
            reports=load_reports(session,observation_days=cfg.comparison_days,stale_hours=cfg.stale_hours)
            selection=selection_info(session)
            if not reports or not selection:
                raise SystemExit("Missing audited repository selection; refusing empty snapshot")
            if not any(r["issue_rows"] or r["pr_rows"] or r["ci_rows"] for r in reports):
                raise SystemExit("No public GitHub source records were collected; no snapshot produced")
            print(json.dumps(export_snapshot(SNAPSHOT_PATH,reports,selection),indent=2))
    finally:
        engine.dispose()

if __name__=="__main__":
    main()
