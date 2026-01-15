from time import time
from datetime import datetime, timezone, timedelta
from sib_api_v3_sdk.rest import ApiException
from typing import Any
import re, secrets, stripe
import sib_api_v3_sdk

from app.core.config import _PUBLIC_BUSINESS_CACHE, TIME_TO_LIVE, settings
from app.db.models import Business

if not settings.BREVO_API_KEY:
    raise RuntimeError("BREVO_API_KEY is not set")

config = sib_api_v3_sdk.Configuration()
config.api_key["api-key"] = settings.BREVO_API_KEY

client = sib_api_v3_sdk.ApiClient(config)
brevo = sib_api_v3_sdk.TransactionalEmailsApi(client)


#Convert business name to URL safe slug
def slugify(name: str) -> str:
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]", "", slug)
    return slug


#Retrieve cached public business data if fresh
def get_cached_business(slug: str):
    entry = _PUBLIC_BUSINESS_CACHE.get(slug)
    if not entry:
        return None

    value, timestamp = entry
    if time() - timestamp > TIME_TO_LIVE:
        del _PUBLIC_BUSINESS_CACHE[slug]
        return None

    return value


#Store a public business data in cache with a timestamp
def set_cached_business(slug: str, data: dict):
    _PUBLIC_BUSINESS_CACHE[slug] = (data, time())


#Generate a secure 6 digit recovery code and its expiry time
def generate_verification_code(minutes_valid: int = 10) -> tuple[str, datetime]:
    code = f"{secrets.randbelow(1_000_000):06d}"
    expires = datetime.now(timezone.utc) + timedelta(minutes=minutes_valid)
    return code, expires


#Convert unix timestamp to timezone aware datetime
def _ts_to_dt(ts: int | None):
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


#Safely fetch live subscription from stripe and update db model
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
    

#Send a transactional email via Brevo using a predefined template
def _send_email(*, to: str, template_id: int, params: dict[str, Any]) -> None:
    try:
        email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": to}],
            template_id=template_id,
            params=params,
        )
        brevo.send_transac_email(email)

    except ApiException as e:
        raise RuntimeError(
            f"Brevo email failed (template {template_id})"
        ) from e
    
    
#Format booking date and time consistently for email templates
def _format_booking_time(start_time: datetime) -> tuple[str, str]:
    return (
        start_time.strftime("%A, %d %B %Y"),
        start_time.strftime("%H:%M"),
    )