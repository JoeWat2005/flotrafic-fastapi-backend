from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session
import stripe
from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.db.models import Business
from app.services.audit import log_action
from app.core.config import settings

router = APIRouter(prefix="/stripe", tags=["Stripe"])

stripe.api_key = settings.STRIPE_SECRET_KEY
WEBHOOK_SECRET = settings.STRIPE_WEBHOOK_SECRET


def _ts_to_dt(ts: int | None):
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def _safe_stripe_subscription_refresh(business: Business):
    """
    Best-effort refresh of subscription status + period end.
    Never raises.
    """
    sub_id = business.stripe_subscription_id
    if not sub_id:
        return

    try:
        sub = stripe.Subscription.retrieve(sub_id)
        business.stripe_subscription_status = getattr(sub, "status", None)
        business.stripe_current_period_end = _ts_to_dt(
            getattr(sub, "current_period_end", None)
        )
    except Exception:
        # Stripe eventual consistency / transient errors – ignore
        return


@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature")

    # Stripe expects 4xx on signature/payload issues
    if not sig:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig,
            secret=WEBHOOK_SECRET,
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook payload")

    db: Session = SessionLocal()

    try:
        event_type = event.get("type")
        obj = (event.get("data") or {}).get("object") or {}

        # Default: do nothing but acknowledge
        handled = False

        # =========================
        # CHECKOUT COMPLETED
        # =========================
        if event_type == "checkout.session.completed":
            metadata = obj.get("metadata") or {}
            business_id = metadata.get("business_id")

            if business_id:
                business = db.query(Business).get(int(business_id))
            else:
                business = None

            if business:
                # Persist Stripe IDs from checkout session
                business.stripe_customer_id = obj.get("customer") or business.stripe_customer_id
                business.stripe_subscription_id = obj.get("subscription") or business.stripe_subscription_id

                # Best-effort subscription refresh
                _safe_stripe_subscription_refresh(business)

                # Activate if Stripe says active/trialing
                if business.stripe_subscription_status in ("active", "trialing"):
                    business.is_active = True

                db.commit()

                log_action(
                    db=db,
                    actor_type="system",
                    actor_id=business.id,
                    action="stripe.checkout.session.completed",
                    details=f"sub={business.stripe_subscription_id} status={business.stripe_subscription_status}",
                )

                handled = True

        # =========================
        # SUBSCRIPTION UPDATED
        # =========================
        elif event_type == "customer.subscription.updated":
            sub_id = obj.get("id")
            if sub_id:
                business = (
                    db.query(Business)
                    .filter(Business.stripe_subscription_id == sub_id)
                    .first()
                )
            else:
                business = None

            if business:
                status = obj.get("status")
                business.stripe_subscription_status = status
                business.stripe_current_period_end = _ts_to_dt(obj.get("current_period_end"))

                # Hard lock based on Stripe status
                business.is_active = status in ("active", "trialing")

                db.commit()

                log_action(
                    db=db,
                    actor_type="system",
                    actor_id=business.id,
                    action="stripe.subscription.updated",
                    details=f"status={status}",
                )

                handled = True

        # =========================
        # INVOICE PAID (backup activation signal)
        # =========================
        elif event_type == "invoice.paid":
            sub_id = obj.get("subscription")
            cust_id = obj.get("customer")

            business = None
            if sub_id:
                business = (
                    db.query(Business)
                    .filter(Business.stripe_subscription_id == sub_id)
                    .first()
                )

            # Fallback: match by customer
            if not business and cust_id:
                business = (
                    db.query(Business)
                    .filter(Business.stripe_customer_id == cust_id)
                    .first()
                )

            if business:
                # If we got sub_id but DB doesn't have it yet, store it
                if sub_id and not business.stripe_subscription_id:
                    business.stripe_subscription_id = sub_id

                # Best-effort refresh to get accurate status + period end
                _safe_stripe_subscription_refresh(business)

                if business.stripe_subscription_status in ("active", "trialing"):
                    business.is_active = True

                db.commit()

                log_action(
                    db=db,
                    actor_type="system",
                    actor_id=business.id,
                    action="stripe.invoice.paid",
                    details=f"sub={sub_id}",
                )

                handled = True

        # Acknowledge everything to Stripe
        return {"status": "ok", "handled": handled}

    finally:
        db.close()

