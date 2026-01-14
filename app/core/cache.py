from time import time

_PUBLIC_BUSINESS_CACHE = {}
TTL = 60  # seconds

def get_cached_business(slug: str):
    entry = _PUBLIC_BUSINESS_CACHE.get(slug)
    if not entry:
        return None

    value, timestamp = entry
    if time() - timestamp > TTL:
        del _PUBLIC_BUSINESS_CACHE[slug]
        return None

    return value

def set_cached_business(slug: str, data: dict):
    _PUBLIC_BUSINESS_CACHE[slug] = (data, time())
