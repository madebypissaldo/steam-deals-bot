"""In-memory abuse protections for public Telegram searches."""

from collections import deque
import threading
import time


MIN_SEARCH_INTERVAL_SECONDS = 2
BURST_LIMIT = 5
BURST_WINDOW_SECONDS = 10
MAX_CONCURRENT_SEARCHES = 4

_lock = threading.Lock()
_search_times: dict[str, deque[float]] = {}
_active_requests: set[str] = set()
_global_searches = threading.BoundedSemaphore(MAX_CONCURRENT_SEARCHES)


def start_search(user_id: int | str, now: float | None = None) -> str | None:
    """Reserve capacity for one expensive search, or return a rejection reason."""
    now = time.monotonic() if now is None else now
    key = str(user_id)
    with _lock:
        timestamps = _search_times.setdefault(key, deque())
        while timestamps and now - timestamps[0] >= BURST_WINDOW_SECONDS:
            timestamps.popleft()
        if key in _active_requests:
            return "active"
        if timestamps and now - timestamps[-1] < MIN_SEARCH_INTERVAL_SECONDS:
            return "rate"
        if len(timestamps) >= BURST_LIMIT:
            return "rate"
        if not _global_searches.acquire(blocking=False):
            return "global"
        timestamps.append(now)
        _active_requests.add(key)
    return None


def finish_search(user_id: int | str) -> None:
    key = str(user_id)
    with _lock:
        if key not in _active_requests:
            return
        _active_requests.remove(key)
        _global_searches.release()


def reset_for_tests() -> None:
    """Clear process-local protections for deterministic unit tests."""
    global _global_searches
    with _lock:
        _search_times.clear()
        _active_requests.clear()
        _global_searches = threading.BoundedSemaphore(MAX_CONCURRENT_SEARCHES)
