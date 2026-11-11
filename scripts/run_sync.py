"""Run read-only discovery (optional) + bounded incremental synchronization."""
from pathlib import Path
import sys
import argparse
from sqlalchemy import select, func
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.config.settings import Settings
from src.collectors.client import GitHubClient
from src.collectors.sync import synchronize, sync_lock
from src.database.store import make_engine, init_db, session_factory
from src.database.models import Repository
from src.discovery.selection import select_repositories


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--discover",action="store_true",help="Run audited selection (initial discovery only, not in normal schedule)")
    parser.add_argument("--reconcile",action="store_true",help="Revisit full configured backfill window")
    args=parser.parse_args()
    cfg=Settings.from_env()
    client=GitHubClient(cfg.github_token,cfg.timeout_seconds,cfg.max_retries)
    engine=make_engine(cfg.database_url)
    init_db(engine)
    with sync_lock(engine):
        with session_factory(engine)() as session:
            count=session.scalar(select(func.count()).select_from(Repository).where(Repository.selected.is_(True)))
            if args.discover:
                if count:
                    print("Existing selection preserved; skipping auto reselection. New selection requires an explicit curation procedure.")
                else:
                    result=select_repositories(client,session,cfg)
                    print("Discovery:",result)
            results=synchronize(session,client,cfg,reconcile=args.reconcile)
            for row in results: print(row)
            if not results:
                print("No selected repositories. Run scripts/run_sync.py --discover when GitHub API is accessible.")
                raise SystemExit(2)
            if any(r["status"] != "complete" for r in results):
                print("Some sources failed or are partial; existing records and checkpoint success times were preserved.")
                raise SystemExit(1)
    engine.dispose()

if __name__=="__main__":main()
