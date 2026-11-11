"""Restore previous verified public data before continuing a GitHub Actions sync."""
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.analytics.snapshot import SNAPSHOT_PATH
from src.collectors.restore import hydrate_snapshot
from src.config.settings import Settings
from src.database.store import make_engine, init_db, session_factory

def main():
    engine = make_engine(Settings.from_env().database_url)
    try:
        init_db(engine)
        with session_factory(engine)() as session:
            print(json.dumps(hydrate_snapshot(session, SNAPSHOT_PATH)))
    finally:
        engine.dispose()

if __name__ == "__main__":
    main()
