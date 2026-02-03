from time import time
from datetime import datetime, timezone, timedelta
from sib_api_v3_sdk.rest import ApiException
from typing import Any
import re, secrets, stripe
import sib_api_v3_sdk

from app.core.config import _PUBLIC_BUSINESS_CACHE, TIME_TO_LIVE, settings, apply_subscription_state
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
        sub = stripe.Subscription.retrieve(
            business.stripe_subscription_id,
            expand=["items.data", "latest_invoice"]
        )
    except stripe.error.InvalidRequestError as e:
        # If subscription doesn't exist (e.g. deleted in Stripe but webhook missed)
        if "No such subscription" in str(e):
            business.stripe_subscription_id = None
            business.stripe_subscription_status = "canceled"
            business.stripe_cancel_at_period_end = False
            business.stripe_current_period_end = None
            business.stripe_ended_at = datetime.now(timezone.utc)
            return
        raise e
    except Exception:
        # Avoid crashing for network issues, but maybe log
        raise

    # 1. Update basic fields from subscription object
    business.stripe_subscription_status = sub.status
    business.stripe_cancel_at_period_end = sub.cancel_at_period_end
    business.stripe_ended_at = _ts_to_dt(sub.ended_at)
    # Safely extract current period end

    # Safely extract current period end (Stripe-safe)
    period_end = None

    # Stripe may include this at the subscription level (rare)
    if isinstance(sub, dict) and sub.get("current_period_end"):
        period_end = sub["current_period_end"]

    # Canonical source: subscription items
    elif (
        isinstance(sub, dict)
        and sub.get("items")
        and sub["items"].get("data")
        and len(sub["items"]["data"]) > 0
    ):
        period_end = sub["items"]["data"][0].get("current_period_end")

    if period_end:
        business.stripe_current_period_end = _ts_to_dt(period_end)


    # 2. Derive latest_paid_period_end from INVOICE (Authoritative Access)
    # We prefer the 'latest_invoice' expanded object if available and paid.
    # Otherwise, we might consider fetching the list of invoices if latest_invoice is null/unpaid but that's expensive.
    # For now, relying on latest_invoice is standard.
    
    invoice = sub.latest_invoice

    # PRIMARY PATH: latest_invoice
    if invoice and invoice.status == "paid":
        lines = invoice.lines.data
        max_end = 0

        for line in lines:
            if line.period and line.period.end:
                max_end = max(max_end, line.period.end)

        if max_end:
            business.latest_paid_period_end = _ts_to_dt(max_end)

        # FALLBACK: fetch recent invoices if latest_invoice is missing/stale
    if not business.latest_paid_period_end:
        invoices = stripe.Invoice.list(
            subscription=business.stripe_subscription_id,
            limit=5,
        )

        found = False
        for inv in invoices.data:
            if inv.status != "paid":
                continue

            for line in inv.lines.data:
                if line.period and line.period.end:
                    business.latest_paid_period_end = _ts_to_dt(line.period.end)
                    found = True
                    break

            if found:
                break

    # Note: We do NOT call apply_subscription_state here automatically.
    # The caller should do it to update the tier/is_active derived flags.



    

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