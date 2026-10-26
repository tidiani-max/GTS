"""Small in-process sliding-window rate limiter (per client IP + bucket).
Note: counters are per process. Behind several replicas, move this to Redis or the reverse proxy."""
import time
from collections import defaultdict, deque

from fastapi import Request

from .config import get_settings
from .errors import ApiError

_hits: dict[str, deque] = defaultdict(deque)


def client_ip(request: Request) -> str:
    if get_settings().trust_proxy_headers:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def limit(bucket: str, spec: str):
    """FastAPI dependency factory. spec = 'max/window_seconds'; read lazily so tests can change settings."""
    def dep(request: Request) -> None:
        s = get_settings()
        if not s.rate_limit_enabled:
            return
        max_req, window = (int(x) for x in getattr(s, spec).split("/"))
        key, now = f"{bucket}:{client_ip(request)}", time.monotonic()
        q = _hits[key]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= max_req:
            raise ApiError(429, "rate_limited", "Trop de requêtes. Réessayez plus tard.",
                           headers={"Retry-After": str(int(window - (now - q[0])) + 1)})
        q.append(now)
    return dep


def reset() -> None:
    _hits.clear()
