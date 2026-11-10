"""Minimal in-memory sliding-window rate limiter for sensitive endpoints.

Suitable for a single-process demo deployment. For multi-instance production use a shared
store (e.g. Redis via Flask-Limiter).
"""
import threading
import time
from collections import defaultdict, deque
from functools import wraps
from flask import current_app, jsonify, request

_lock = threading.Lock()
_hits: dict[str, deque] = defaultdict(deque)


def _client_key(bucket: str) -> str:
    return f"{bucket}:{request.remote_addr or 'unknown'}"


def reset_rate_limits():
    with _lock:
        _hits.clear()


def rate_limited(bucket: str):
    """Decorator: reject with 429 when the client exceeds the configured limit for `bucket`."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if current_app.config.get("RATE_LIMIT_ENABLED", True):
                limit, window = current_app.config.get("RATE_LIMITS", {}).get(bucket, (30, 60))
                now = time.monotonic()
                key = _client_key(bucket)
                with _lock:
                    q = _hits[key]
                    while q and now - q[0] > window:
                        q.popleft()
                    if len(q) >= limit:
                        retry = int(window - (now - q[0])) + 1
                        resp = jsonify({
                            "success": False,
                            "error": "Too many requests. Please wait a moment and try again.",
                            "code": "RATE_LIMITED"
                        })
                        resp.headers["Retry-After"] = str(retry)
                        return resp, 429
                    q.append(now)
            return fn(*args, **kwargs)
        return wrapper
    return decorator
