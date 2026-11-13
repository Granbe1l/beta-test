"""Run read-only discovery (optional) + bounded incremental synchronization."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import sys
import argparse
from sqlalchemy import select, func
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.config.settings import Settings
from src.collectors.client import GitHubClient
from src.collectors.sync import synchronize, sync_lock
from src.database.store import make_engine, init_db, session_factory
from src.database.models import Repository
from src.discovery.selection import select_repositories, expand_repositories
from src.database.models import SelectionRun


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--discover",action="store_true",help="Run audited selection (initial discovery only, not in normal schedule)")
    parser.add_argument("--reconcile",action="store_true",help="Revisit full configured backfill window")
    parser.add_argument("--expand", action="store_true", help="Expand vetted selection toward MAX_REPOS without removing existing repositories")
    parser.add_argument("--initial-batch", type=int, default=0, help="New-repository bootstrap limit; all repos update after seeding")
    parser.add_argument("--max-requests", type=int, default=0, help="Bound entire collection run to avoid rate-limit exhaustion")
    parser.add_argument("--audit-open-backlog", action="store_true",
                        help="Use spare API budget for independent full-open-Issue scans")
    parser.add_argument("--repair-coverage", action="store_true",
                        help="Bounded 28d reattempt for up to four low-page Issue/PR sources with short checkpoints")
    args=parser.parse_args()
    cfg=Settings.from_env()
    client=GitHubClient(cfg.github_token,cfg.timeout_seconds,cfg.max_retries,
                        max_requests=args.max_requests or None)
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
            if args.expand and count < cfg.max_repos:
                last_run = session.scalars(select(SelectionRun).order_by(SelectionRun.id.desc())).first()
                previous_expansion = (last_run.parameters or {}).get("discovered_at") if last_run and (last_run.parameters or {}).get("purpose") == "expansion" else None
                if previous_expansion:
                    try:
                        elapsed = datetime.now(timezone.utc) - datetime.fromisoformat(previous_expansion)
                    except (ValueError, TypeError):
                        elapsed = timedelta(days=8)
                else:
                    elapsed = timedelta(days=8)
                if elapsed >= timedelta(days=7):
                    print("Expanding verified repository selection:", expand_repositories(client, session, cfg))
                else:
                    print("Keeping audited selection; expansion already attempted")
            results=synchronize(session,client,cfg,reconcile=args.reconcile,
                                initial_batch_size=args.initial_batch or None,
                                audit_open_backlog=args.audit_open_backlog,
                                repair_coverage=args.repair_coverage)
            for row in results: print(row)
            if not results:
                print("No selected repositories. Run scripts/run_sync.py --discover when GitHub API is accessible.")
                raise SystemExit(2)
            print(f"GitHub API attempts this run: {client.request_count}")
            if any(r["status"] != "complete" for r in results):
                print("Some sources failed or are partial; existing records and checkpoint success times were preserved.")
                raise SystemExit(1)
    engine.dispose()

if __name__=="__main__":main()
