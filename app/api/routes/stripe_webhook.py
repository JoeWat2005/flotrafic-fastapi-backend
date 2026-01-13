from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session
import stripe
from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.db.models import Business
from app.services.audit import log_action
from app.services.email import (
    send_subscription_activated_email,
    send_subscription_cancelled_email,
    send_account_paused_email,
    send_subscription_plan_changed_email,
)
from app.core.config import settings

router = APIRouter(prefix="/stripe", tags=["Stripe"])

stripe.api_key = settings.STRIPE_SECRET_KEY
WEBHOOK_SECRET = settings.STRIPE_WEBHOOK_SECRET


def _ts_to_dt(ts: int | None):
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def _safe_stripe_subscription_refresh(business: Business):
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
        return


@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature")

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
        handled = False

        # =========================
        # CHECKOUT COMPLETED
        # =========================
        if event_type == "checkout.session.completed":
            metadata = obj.get("metadata") or {}
            business_id = metadata.get("business_id")

            business = (
                db.query(Business).get(int(business_id))
                if business_id
                else None
            )

            if business:
                business.stripe_customer_id = obj.get("customer")
                business.stripe_subscription_id = obj.get("subscription")

                _safe_stripe_subscription_refresh(business)

                if business.stripe_subscription_status in ("active", "trialing"):
                    business.is_active = True

                    send_subscription_activated_email(
                        business_email=business.email,
                        tier=metadata.get("tier", "foundation"),
                    )

                db.commit()
                handled = True

        # =========================
        # CURRENT PERIOD END    
        # =========================

        elif event_type == "invoice.paid":
            sub_id = obj.get("subscription")

            business = (
                db.query(Business)
                .filter(Business.stripe_subscription_id == sub_id)
                .first()
                if sub_id
                else None
            )

            if business:
                _safe_stripe_subscription_refresh(business)
                business.is_active = True
                db.commit()
                handled = True

        # =========================
        # SUBSCRIPTION UPDATED
        # =========================
        elif event_type == "customer.subscription.updated":
            sub_id = obj.get("id")

            business = (
                db.query(Business)
                .filter(Business.stripe_subscription_id == sub_id)
                .first()
                if sub_id
                else None
            )

            if business:
                old_tier = business.tier

                # Determine new tier from price ID
                items = obj.get("items", {}).get("data", [])
                price_id = items[0]["price"]["id"] if items else None

                if price_id == settings.FOUNDATION_PRICE_ID:
                    new_tier = "foundation"
                elif price_id == settings.MANAGED_PRICE_ID:
                    new_tier = "managed"
                elif price_id == settings.AUTOPILOT_PRICE_ID:
                    new_tier = "autopilot"
                else:
                    new_tier = old_tier  # fallback safety

                business.tier = new_tier
                business.stripe_subscription_status = obj.get("status")
                business.stripe_current_period_end = _ts_to_dt(
                    obj.get("current_period_end")
                )
                business.is_active = business.stripe_subscription_status in (
                    "active",
                    "trialing",
                )

                db.commit()

                # ✅ Only email if tier actually changed
                if old_tier and old_tier != new_tier:
                    send_subscription_plan_changed_email(
                        business_email=business.email,
                        old_tier=old_tier,
                        new_tier=new_tier,
                    )

                handled = True

        # =========================
        # SUBSCRIPTION CANCELLED
        # =========================
        elif event_type == "customer.subscription.deleted":
            sub_id = obj.get("id")

            business = (
                db.query(Business)
                .filter(Business.stripe_subscription_id == sub_id)
                .first()
                if sub_id
                else None
            )

            if business:
                business.is_active = False
                business.stripe_subscription_status = "canceled"
                db.commit()

                send_subscription_cancelled_email(
                    business_email=business.email
                )

                handled = True

        # =========================
        # PAYMENT FAILED
        # =========================
        elif event_type == "invoice.payment_failed":
            sub_id = obj.get("subscription")
            cust_id = obj.get("customer")

            business = None
            if sub_id:
                business = (
                    db.query(Business)
                    .filter(Business.stripe_subscription_id == sub_id)
                    .first()
                )

            if not business and cust_id:
                business = (
                    db.query(Business)
                    .filter(Business.stripe_customer_id == cust_id)
                    .first()
                )

            if business:
                business.is_active = False
                business.stripe_subscription_status = "past_due"
                db.commit()

                send_account_paused_email(
                    business_email=business.email
                )

                handled = True

        return {"status": "ok", "handled": handled}

    finally:
        db.close()


