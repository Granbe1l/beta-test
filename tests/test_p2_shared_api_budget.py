"""Rolling public inspector budget: process-wide, lock-protected, cache misses only."""
from concurrent.futures import ThreadPoolExecutor

from src.analytics.public_rate_limit import RollingInspectionBudget


def test_budget_blocks_only_after_actual_uncached_attempts_and_recovers():
    now = [100.0]
    budget = RollingInspectionBudget(limit=3, window_seconds=30,
                                     clock=lambda: now[0])
    assert [budget.try_acquire() for _ in range(3)] == [
        (True, 0), (True, 0), (True, 0)]
    assert budget.try_acquire() == (False, 30)
    assert budget.used() == 3
    now[0] += 29.1
    assert budget.try_acquire() == (False, 1)
    now[0] += .9
    assert budget.try_acquire() == (True, 0)
    assert budget.used() == 1


def test_budget_is_atomic_under_concurrent_distinct_lookups():
    now = [0.0]
    budget = RollingInspectionBudget(limit=4, window_seconds=3600,
                                     clock=lambda: now[0])
    with ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(lambda _: budget.try_acquire()[0], range(30)))
    assert sum(results) == 4
    assert budget.used() == 4


def test_invalid_budget_settings_refused():
    for limit, seconds in ((0, 30), (2, 0), (-1, 20)):
        try:
            RollingInspectionBudget(limit=limit, window_seconds=seconds)
        except ValueError:
            pass
        else:
            raise AssertionError("Rate budget must validate its bounds")


def test_shared_budget_only_runs_on_a_uncached_inspection_miss():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] /
              "src/ui/repo_lookup.py").read_text(encoding="utf-8")
    assert "@st.cache_resource(show_spinner=False)" in source
    assert "@st.cache_data(ttl=300, show_spinner=False, max_entries=64)" in source
    cache_function = source.split(
        "def _cached_public_preview(repository: str):", 1)[1].split(
        "def _short(", 1)[0]
    assert cache_function.index("try_acquire()") < cache_function.index(
        "inspect_public_repository(repository)")
    assert "RollingInspectionBudget(limit=12, window_seconds=3600)" in source
    assert "public_inspector_last_retry" in source
    assert "temporarily at its shared" in source
