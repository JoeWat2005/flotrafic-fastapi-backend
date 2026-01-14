from time import time

_RATE_LIMIT_STORE = {}

def rate_limit(key: str, max_requests: int, window_seconds: int) -> bool:
    now = time()
    timestamps = _RATE_LIMIT_STORE.get(key, [])

    timestamps = [t for t in timestamps if now - t < window_seconds]

    if len(timestamps) >= max_requests:
        _RATE_LIMIT_STORE[key] = timestamps
        return False

    timestamps.append(now)
    _RATE_LIMIT_STORE[key] = timestamps
    return True

def make_key(slug: str, request, endpoint: str) -> str:
    ip = request.client.host if request.client else "unknown"
    return f"{slug}:{endpoint}:{ip}"
