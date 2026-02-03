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
from app.core.config import settings, apply_subscription_state

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

    print("🔔 Stripe webhook received")
    print("Signature present:", bool(sig))
    print("Payload length:", len(payload))

    if not sig:
        print("❌ Missing stripe-signature header")
        raise HTTPException(status_code=400, detail="Missing Stripe signature")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig,
            secret=WEBHOOK_SECRET,
        )

        # ✅ SAFE TO DEBUG NOW
        print("✅ Webhook verified")
        print("Event ID:", event.get("id"))
        print("Event type:", event.get("type"))

        obj = (event.get("data") or {}).get("object") or {}
        print("Object type:", obj.get("object"))
        print("Object keys:", list(obj.keys()))

    except stripe.error.SignatureVerificationError as e:
        print("❌ Signature verification failed:", str(e))
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    except Exception as e:
        print("❌ Webhook parse failed:", str(e))
        raise HTTPException(status_code=400, detail="Invalid webhook payload")

    db: Session = SessionLocal()

    try:
        event_id = event.get("id")
        event_type = event.get("type")
        obj = (event.get("data") or {}).get("object") or {}
        handled = False

        # Prevent duplicate webhook processing
        if db.get(StripeEvent, event_id):
            return {"status": "ok", "handled": True, "duplicate": True}

        # ------------------------------------------------------------------
        # CHECKOUT COMPLETED
        # ------------------------------------------------------------------
        if event_type == "checkout.session.completed":
            metadata = obj.get("metadata") or {}
            business_id = metadata.get("business_id")

            business = db.get(Business, int(business_id)) if business_id else None

            if business:
                business.stripe_customer_id = obj.get("customer")
                business.stripe_subscription_id = obj.get("subscription")

                # ❗ DO NOT refresh subscription here
                # Stripe has not finished creating it yet

                db.commit()

                log_action(
                    db=db,
                    actor_type="system",
                    actor_id=business.id,
                    action="billing.checkout_completed",
                )

                handled = True
                db.add(StripeEvent(event_id=event_id))
                db.commit()


        # ------------------------------------------------------------------
        # SUBSCRIPTION UPDATED / CREATED (Refreshes everything)
        # ------------------------------------------------------------------
        elif event_type in ("customer.subscription.updated", "customer.subscription.created"):
            sub_id = obj.get("id")

            business = (
                db.query(Business)
                .filter(Business.stripe_subscription_id == sub_id)
                .first()
            )

            if business:

                old_tier = business.tier

                # 1. Full Refresh from Stripe (updates status, cancel_at, ended_at, latest_invoice)
                _safe_stripe_subscription_refresh(business)
                apply_subscription_state(business)
                db.commit()

                print(f"WEBHOOK: {event_type} handled")
                print(f"  Sub: {business.stripe_subscription_status}")
                print(f"  Tier: {business.tier}")
                print(f"  Invoice Exp: {business.latest_paid_period_end}")

                if old_tier != business.tier:
                    log_action(
                        db=db,
                        actor_type="system",
                        actor_id=business.id,
                        action="billing.tier_updated",
                        details=f"{old_tier}->{business.tier}",
                    )

                    send_subscription_plan_changed_email(
                        business_email=business.email,
                        old_tier=old_tier,
                        new_tier=business.tier,
                    )

                handled = True
                db.add(StripeEvent(event_id=event_id))
                db.commit()

        # ------------------------------------------------------------------
        # INVOICE PAID / SUCCEEDED (Updates access coverage)
        # ------------------------------------------------------------------
        elif event_type in ("invoice.paid", "invoice.payment_succeeded"):
            # If an invoice is paid, we should update the business's latest_paid_period_end
            sub_id = obj.get("subscription")
            if sub_id:
                business = (
                    db.query(Business)
                    .filter(Business.stripe_subscription_id == sub_id)
                    .first()
                )
                if business:
                     # Refresh logic will pull this invoice if it's latest.
                     # Or we can manually parse this event object to save a call.
                     # For robustness, let's just trigger a safe refresh which fetches the authoritative state.
                     _safe_stripe_subscription_refresh(business)
                     apply_subscription_state(business)
                     db.commit()
                     handled = True
                     db.add(StripeEvent(event_id=event_id))
                     db.commit()
            

        # ------------------------------------------------------------------
        # PAYMENT FAILED → START / CONTINUE GRACE PERIOD
        # ------------------------------------------------------------------
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
                _safe_stripe_subscription_refresh(business)
                apply_subscription_state(business, "past_due")
                db.commit()

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

        # ------------------------------------------------------------------
        # SUBSCRIPTION CANCELLED
        # ------------------------------------------------------------------
        elif event_type == "customer.subscription.deleted":
            sub_id = obj.get("id")

            business = (
                db.query(Business)
                .filter(Business.stripe_subscription_id == sub_id)
                .first()
            )

            if business:
                # Mark as canceled in our model, but KEEP authoritative access date
                # We assume "deleted" means immediate cancellation in Stripe terms, 
                # but user might still have paid time left.
                
                business.stripe_subscription_status = "canceled"
                business.stripe_subscription_id = None
                business.stripe_cancel_at_period_end = False
                business.stripe_current_period_end = None
                # business.latest_paid_period_end # Do NOT clear this!
                
                # Recompute: if latest_paid_period_end > now, they stay Pro.
                business.stripe_ended_at = _ts_to_dt(obj.get("ended_at")) or business.stripe_ended_at
                apply_subscription_state(business)
                db.commit()

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
                db.add(StripeEvent(event_id=event_id))
                db.commit()

        # ------------------------------------------------------------------
        # INVOICE PAID → STRIPE MAY RECOVER SUBSCRIPTION (Handled above now)
        # ------------------------------------------------------------------
        # elif event_type == "invoice.paid": ... (merged above)

        # ------------------------------------------------------------------
        # RECORD EVENT + COMMIT
        # ------------------------------------------------------------------

        return {"status": "ok", "handled": handled}

    finally:
        db.close()
