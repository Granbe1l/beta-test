"""Read-only GitHub REST client with bounded pagination and rate-limit retries."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import random
import time
from urllib.parse import urlsplit
import requests

API_BASE = "https://api.github.com"


class GitHubAPIError(RuntimeError):
    pass


@dataclass
class PageResult:
    items: list[dict]
    pages: int
    complete: bool
    cap_reached: bool
    cutoff_reached: bool


class GitHubClient:
    def __init__(self, token=None, timeout=20, max_retries=4, session=None, sleeper=time.sleep):
        self.session = session or requests.Session()
        self.timeout = timeout
        self.max_retries = max_retries
        self.sleep = sleeper
        self.session.headers.update({"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "DeliveryMonitor-ReadOnly/1.0"})
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    def get(self, path: str, params=None):
        if path.startswith("https://"):
            parts = urlsplit(path)
            if parts.netloc != "api.github.com":
                raise ValueError("Only api.github.com is permitted")
            url = path
        else:
            if not path.startswith("/"):
                raise ValueError("Expected GitHub API path")
            url = API_BASE + path
        for attempt in range(self.max_retries + 1):
            try:
                res = self.session.get(url, params=params, timeout=self.timeout)
            except (requests.Timeout, requests.ConnectionError) as exc:
                if attempt == self.max_retries:
                    raise GitHubAPIError(f"GitHub connection failure: {type(exc).__name__}") from exc
                self.sleep(min(2 ** attempt + random.uniform(0, 0.2), 30))
                continue
            if res.status_code == 200:
                return res.json(), res
            if res.status_code in (403, 429, 500, 502, 503, 504) and attempt < self.max_retries:
                limit_reset = res.headers.get("X-RateLimit-Reset")
                retry_after = res.headers.get("Retry-After")
                limited = res.headers.get("X-RateLimit-Remaining") == "0"
                delay = max(1.0, 2 ** attempt + random.uniform(0, 0.3))
                if retry_after:
                    try: delay = max(delay, float(retry_after))
                    except ValueError: pass
                elif limited and limit_reset:
                    try: delay = max(delay, int(limit_reset) - time.time() + 2)
                    except ValueError: pass
                elif res.status_code in (403, 429):
                    delay = max(delay, 60)  # secondary rate limit without Retry-After
                if delay > 120:
                    raise GitHubAPIError("GitHub rate limit reset exceeds the retry budget")
                self.sleep(delay)
                continue
            raise GitHubAPIError(f"GitHub HTTP {res.status_code} at {urlsplit(url).path}")
        raise GitHubAPIError("GitHub retries exhausted")

    def paginate(self, path: str, params: dict, max_pages: int, cutoff: datetime | None = None, sort_key: str = "updated_at", wrapper: str | None = None) -> PageResult:
        """Pages are complete only when exhausted or a correctly sorted cutoff is reached.

        Each paged request uses its own page number rather than trusting arbitrary next URLs.
        """
        items: list[dict] = []
        cutoff_reached = False
        exhausted = False
        last_count = 0
        page_count = 0
        page_size = int(params.get("per_page", 100))
        for page in range(1, max_pages + 1):
            data, response = self.get(path, {**params, "page": page})
            page_count += 1
            batch = data.get(wrapper, []) if wrapper else data
            if not isinstance(batch, list):
                raise GitHubAPIError("Unexpected GitHub pagination response")
            last_count = len(batch)
            for item in batch:
                if cutoff is not None:
                    iso = item.get(sort_key)
                    if iso:
                        timestamp = datetime.fromisoformat(iso.replace("Z", "+00:00"))
                        if timestamp < cutoff:
                            cutoff_reached = True
                            continue
                items.append(item)
            if cutoff_reached:
                # Valid only for descending order by sort_key (caller responsibility).
                break
            if last_count < page_size:
                exhausted = True
                break
            if 'next' not in response.links:
                exhausted = True
                break
        complete = cutoff_reached or exhausted
        return PageResult(items, page_count, complete, not complete, cutoff_reached)
