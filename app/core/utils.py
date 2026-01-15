from time import time
from datetime import datetime, timezone, timedelta
import re, secrets, stripe

from app.core.config import _PUBLIC_BUSINESS_CACHE, TIME_TO_LIVE
from app.db.models import Business

#convert business name to URL safe slug
def slugify(name: str) -> str:
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]", "", slug)
    return slug

#retrieve cached public business data if fresh
def get_cached_business(slug: str):
    entry = _PUBLIC_BUSINESS_CACHE.get(slug)
    if not entry:
        return None

    value, timestamp = entry
    if time() - timestamp > TIME_TO_LIVE:
        del _PUBLIC_BUSINESS_CACHE[slug]
        return None

    return value

#store a public business data in cache with a timestamp
def set_cached_business(slug: str, data: dict):
    _PUBLIC_BUSINESS_CACHE[slug] = (data, time())

#generate a secure 6 digit recovery code and its expiry time
def generate_verification_code(minutes_valid: int = 10) -> tuple[str, datetime]:
    code = f"{secrets.randbelow(1_000_000):06d}"
    expires = datetime.now(timezone.utc) + timedelta(minutes=minutes_valid)
    return code, expires

#convert unix timestamp to timezone aware datetime
def _ts_to_dt(ts: int | None):
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


#safely fetch live subscription from stripe and update db model
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