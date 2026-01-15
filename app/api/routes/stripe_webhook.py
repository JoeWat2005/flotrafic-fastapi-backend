from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session
import stripe

from app.core.utils import _ts_to_dt, _safe_stripe_subscription_refresh
from app.db.session import SessionLocal
from app.db.models import Business, StripeEvent
from app.services.audit import log_action
from app.services.email import (
    send_subscription_activated_email,
    send_subscription_cancelled_email,
    send_account_paused_email,
    send_subscription_plan_changed_email,
)
from app.core.config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY
WEBHOOK_SECRET = settings.STRIPE_WEBHOOK_SECRET

router = APIRouter(prefix="/stripe", tags=["Stripe"])


"""
STRIPE WEBHOOK ROUTES => BILLING EVENT HANDLERS

Receives and processes Stripe webhook events
to keep subscription state in sync.
"""


#Receive and validate incoming Stripe webhook events
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
        event_id = event.get("id")
        event_type = event.get("type")
        obj = (event.get("data") or {}).get("object") or {}
        handled = False

        #handle duplicate events
        already_handled = db.get(StripeEvent, event_id)
        if already_handled:
            return {"status": "ok", "handled": True, "duplicate": True}


        #Handle successful checkout completion and subscription activation
        if event_type == "checkout.session.completed":
            metadata = obj.get("metadata") or {}
            business_id = metadata.get("business_id")

            business = (
                db.get(Business, int(business_id))
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

                log_action(
                    db=db,
                    actor_type="system",
                    actor_id=business.id,
                    action="billing.subscription_created",
                    details=f"tier={metadata.get('tier')}",
                )

                handled = True

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
                handled = True

        #Handle subscription updates including tier changes
        elif event_type == "customer.subscription.updated":
            sub_id = obj.get("id")

            business = (
                db.query(Business)
                .filter(Business.stripe_subscription_id == sub_id)
                .first()
            )

            if business:
                old_tier = business.tier

                status = obj.get("status")
                business.stripe_subscription_status = status
                business.stripe_current_period_end = _ts_to_dt(
                    obj.get("current_period_end")
                )

                if status in ("active", "trialing"):
                    new_tier = "pro"
                    business.is_active = True
                else:
                    new_tier = "free"
                    business.is_active = False

                business.tier = new_tier

                log_action(
                    db=db,
                    actor_type="system",
                    actor_id=business.id,
                    action="billing.tier_updated",
                    details=f"{old_tier}->{new_tier}",
                )

                if old_tier != new_tier:
                    send_subscription_plan_changed_email(
                        business_email=business.email,
                        old_tier=old_tier,
                        new_tier=new_tier,
                    )

                handled = True


        #Handle subscription cancellation events
        elif event_type == "customer.subscription.deleted":
            sub_id = obj.get("id")

            business = (
                db.query(Business)
                .filter(Business.stripe_subscription_id == sub_id)
                .first()
            )

            if business:
                business.tier = "free"
                business.is_active = True
                business.stripe_subscription_status = "canceled"

                log_action(
                    db=db,
                    actor_type="system",
                    actor_id=business.id,
                    action="billing.subscription_cancelled",
                )

                send_subscription_cancelled_email(
                    business_email=business.email
                )

                handled = True


        #Handle failed payments and pause affected accounts
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

                log_action(
                    db=db,
                    actor_type="system",
                    actor_id=business.id,
                    action="billing.payment_failed",
                )

                send_account_paused_email(
                    business_email=business.email
                )

                handled = True

        db.add(StripeEvent(event_id=event_id))
        db.commit()
        return {"status": "ok", "handled": handled}

    finally:
        db.close()