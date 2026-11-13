"""Read-only, timestamped GitHub REST API snapshot for PostgreSQL-free preview."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from pathlib import Path
from types import SimpleNamespace
import gzip
import json

from src.analytics.metrics import calculate_ci, calculate_issues, calculate_prs, closure_change, utc
from src.analytics.read import available_source

SNAPSHOT_PATH = Path(__file__).resolve().parents[2] / "data" / "github_public_snapshot.json.gz"
DATE_FIELDS = frozenset({"created_at","updated_at","closed_at","merged_at","pushed_at","selected_at",
                        "started_at","completed_at","last_success_at","high_watermark","coverage_start",
                        "measured_at","fetched_at","finished_at"})

def encode(value):
    if isinstance(value, datetime):
        return utc(value).isoformat()
    raise TypeError(type(value).__name__)

def decode(value):
    if isinstance(value, list):
        return [decode(v) for v in value]
    if isinstance(value, dict):
        return {k:(utc(v) if k in DATE_FIELDS and isinstance(v,str) else decode(v)) for k,v in value.items()}
    return value

def export_snapshot(path: Path, reports: list[dict], selection: dict | None, generated_at=None):
    generated = utc(generated_at or datetime.now(timezone.utc))
    payload = {"schema_version":1,"generated_at":generated,
               "source":"Public GitHub REST API; links to original records",
               "mode":"bounded public snapshot, not a live database",
               "selection":selection,"reports":reports}
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    with gzip.open(tmp,"wb",compresslevel=9) as f:
        f.write(json.dumps(payload,default=encode,ensure_ascii=False,separators=(",",":")).encode("utf-8"))
    tmp.replace(path)
    return {"generated_at":generated.isoformat(),"repositories":len(reports),
            "source_records":{k:sum(len(r[s]) for r in reports) for k,s in
                (("issues","issue_rows"),("pull_requests","pr_rows"),("workflow_runs","ci_rows"))},
            "bytes":path.stat().st_size}

def read_snapshot(path:Path=SNAPSHOT_PATH,observation_days=90,stale_hours=12,now=None):
    now=utc(now or datetime.now(timezone.utc))
    with gzip.open(path,"rb") as f:
        payload=json.loads(f.read())
    if payload.get("schema_version")!=1 or not isinstance(payload.get("reports"),list):
        raise ValueError("Invalid public GitHub snapshot")
    payload=decode(payload)
    generated=utc(payload["generated_at"])
    if generated-now>timedelta(minutes=10):
        raise ValueError("Snapshot time is in the future")
    reports=payload["reports"]
    for r in reports:
        cp=r.get("coverage",{})
        status={s:available_source(SimpleNamespace(**cp[s]),now,stale_hours) if cp.get(s) else "unavailable"
                for s in ("issues","pull_requests","workflow_runs")}
        r["status"]=status
        # A full open-backlog inventory is a separate source, not a
        # substitute for 28-day updated-event coverage.
        r["open_backlog_status"] = (
            available_source(SimpleNamespace(**cp["open_backlog"]), now, stale_hours)
            if cp.get("open_backlog") else "unavailable"
        )
        r["coverage_ok"]=all(x=="complete" for x in status.values())
        r["issues"]=calculate_issues(r.get("issue_rows",[]),now,observation_days,
                                     status["issues"]=="complete",(cp.get("issues") or {}).get("coverage_start"))
        r["prs"]=calculate_prs(r.get("pr_rows",[]),now,observation_days,
                               status["pull_requests"]=="complete",(cp.get("pull_requests") or {}).get("coverage_start"))
        r["ci"]=calculate_ci(r.get("ci_rows",[]),now,observation_days,
                             status["workflow_runs"]=="complete",(cp.get("workflow_runs") or {}).get("coverage_start"))
        r["closure"]=closure_change(r.get("issue_rows",[]),now,
                                     status["issues"]=="complete",(cp.get("issues") or {}).get("coverage_start"))
    return reports,payload.get("selection"),{"mode":"snapshot","generated_at":generated,
                   "stale":(now-generated).total_seconds()>stale_hours*3600}
