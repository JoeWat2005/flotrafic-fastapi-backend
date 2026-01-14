import re
from time import time

_PUBLIC_BUSINESS_CACHE = {}

def slugify(name: str) -> str:
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]", "", slug)
    return slug


TTL = 60

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