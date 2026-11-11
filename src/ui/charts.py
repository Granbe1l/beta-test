"""Descriptive charts based only on retrieved public GitHub records."""
from collections import Counter
from datetime import datetime,timedelta,timezone
from src.analytics.metrics import utc

def category_counts(reports):
    return dict(sorted(Counter(r["repository"].get("category") or "Other" for r in reports).items()))

def observed_age_bands(issues,now=None):
    now=utc(now or datetime.now(timezone.utc))
    counts={"0–6 days":0,"7–29 days":0,"30–89 days":0,"90+ days":0}
    for row in issues:
        if row.get("state")!="open" or not row.get("created_at"):
            continue
        age=(now-utc(row["created_at"])).total_seconds()/86400
        counts["0–6 days" if age<7 else "7–29 days" if age<30 else "30–89 days" if age<90 else "90+ days"]+=1
    return counts

def observed_merge_times(prs,now=None,days=90):
    now=utc(now or datetime.now(timezone.utc))
    counts={"<1 day":0,"1–7 days":0,"7–30 days":0,">30 days":0}
    for row in prs:
        m=utc(row.get("merged_at"))
        c=utc(row.get("created_at"))
        if not m or not c or not now-timedelta(days=days)<=m<=now:
            continue
        d=max(0,(m-c).total_seconds()/86400)
        counts["<1 day" if d<1 else "1–7 days" if d<7 else "7–30 days" if d<=30 else ">30 days"]+=1
    return counts

def source_coverage_counts(reports):
    values=Counter(v for r in reports for v in r["status"].values())
    return {k:values.get(k,0) for k in ("complete","partial","stale","failed","unavailable")}

def observed_outcomes(runs,now=None,days=30):
    now=utc(now or datetime.now(timezone.utc))
    counts={"Success":0,"Failure / timeout":0,"Skipped":0,"Other outcomes":0}
    for row in runs:
        created=utc(row.get("created_at"))
        if not created or not now-timedelta(days=days)<=created<=now or row.get("status")!="completed":
            continue
        label=row.get("conclusion")
        category="Success" if label=="success" else "Failure / timeout" if label in ("failure","timed_out") else "Skipped" if label=="skipped" else "Other outcomes"
        counts[category]+=1
    return counts
