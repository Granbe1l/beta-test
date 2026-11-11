"""Initialize empty local or managed PostgreSQL schema (schema v1)."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.config.settings import Settings
from src.database.store import make_engine, init_db

if __name__ == "__main__":
    cfg=Settings.from_env()
    engine=make_engine(cfg.database_url)
    init_db(engine)
    print("Database schema initialized (no demonstration records inserted)")
    engine.dispose()
