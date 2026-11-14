"""Validate identity, source URL and timestamps before persistence."""
from __future__ import annotations
from datetime import datetime
from urllib.parse import urlsplit


def dt(value, required=True):
    if not value:
        if required: raise ValueError("Missing required timestamp")
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def source_url(raw: dict, expected_segment: str) -> str:
    value = raw.get("html_url", "")
    url = urlsplit(value)
    if url.scheme != "https" or url.netloc != "github.com" or expected_segment not in url.path:
        raise ValueError("Invalid GitHub evidence URL")
    return value


def labels(raw):
    return [str(v.get("name", ""))[:100] for v in raw.get("labels", []) if isinstance(v, dict)]


def issue(raw: dict, repo_id: int) -> dict | None:
    if "pull_request" in raw: return None
    return dict(id=int(raw["id"]), repo_id=repo_id, number=int(raw["number"]),
                url=source_url(raw, "/issues/"), title=raw.get("title") or "(untitled)",
                state=raw["state"], created_at=dt(raw.get("created_at")),
                updated_at=dt(raw.get("updated_at")), closed_at=dt(raw.get("closed_at"), False),
                labels=labels(raw), comments_count=int(raw.get("comments", 0)))


def pull_request(raw: dict, repo_id: int) -> dict:
    account = raw.get("user")
    kind = account.get("type") if isinstance(account, dict) else None
    author_type = kind if kind in {"User", "Bot", "Organization"} else None
    return dict(id=int(raw["id"]), repo_id=repo_id, number=int(raw["number"]),
                url=source_url(raw, "/pull/"), title=raw.get("title") or "(untitled)",
                state=raw["state"], draft=bool(raw.get("draft", False)),
                created_at=dt(raw.get("created_at")), updated_at=dt(raw.get("updated_at")),
                closed_at=dt(raw.get("closed_at"), False), merged_at=dt(raw.get("merged_at"), False),
                labels=labels(raw), author_type=author_type,
                review_comments=raw.get("review_comments") if isinstance(raw.get("review_comments"), int) else None)


def workflow_run(raw: dict, repo_id: int) -> dict:
    url = source_url(raw, "/actions/runs/")
    return dict(id=int(raw["id"]), repo_id=repo_id, url=url,
                workflow_name=raw.get("name") or "Unknown", status=raw.get("status") or "unknown",
                conclusion=raw.get("conclusion"), branch=raw.get("head_branch"),
                event=raw.get("event"), created_at=dt(raw.get("created_at")),
                updated_at=dt(raw.get("updated_at")))
