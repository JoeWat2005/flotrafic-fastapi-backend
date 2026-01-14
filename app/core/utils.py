from time import time
from datetime import datetime, timezone, timedelta
import re, secrets, stripe

from app.db.models import Business

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

def generate_verification_code(minutes_valid: int = 10) -> tuple[str, datetime]:
    code = f"{secrets.randbelow(1_000_000):06d}"
    expires = datetime.now(timezone.utc) + timedelta(minutes=minutes_valid)
    return code, expires

#timestamp to datetime helper function
def _ts_to_dt(ts: int | None):
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


#stripe subscription state fetch helper function
def _safe_stripe_subscription_refresh(business: Business):
    if not business.stripe_subscription_id:
        return

    try:
        sub = stripe.Subscription.retrieve(business.stripe_subscription_id)
        business.stripe_subscription_status = getattr(sub, "status", None)
        business.stripe_current_period_end = _ts_to_dt(
            getattr(sub, "current_period_end", None)
        )

    except Exception:
        return