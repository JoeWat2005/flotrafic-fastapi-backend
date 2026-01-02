from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session
import stripe
import os
from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.db.models import Business
from app.services.audit import log_action

router = APIRouter(prefix="/stripe/webhook", tags=["Stripe"])

WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")


@router.post("/")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig, WEBHOOK_SECRET
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook")

    db: Session = SessionLocal()

    try:
        event_type = event["type"]
        data = event["data"]["object"]

        if event_type in (
            "customer.subscription.created",
            "customer.subscription.updated",
        ):
            subscription_id = data["id"]
            status = data["status"]
            period_end = datetime.fromtimestamp(
                data["current_period_end"], tz=timezone.utc
            )

            # ✅ Find by customer id (works even on first subscription)
            customer_id = data.get("customer")
            business = (
                db.query(Business)
                .filter(Business.stripe_customer_id == customer_id)
                .first()
            )

            if business:
                business.stripe_subscription_id = subscription_id
                business.stripe_subscription_status = status
                business.stripe_current_period_end = period_end

                # 🔑 PLATFORM ENFORCEMENT
                business.is_active = status in ("active", "trialing")

                db.commit()

                log_action(
                    db=db,
                    actor_type="system",
                    actor_id=business.id,
                    action="billing.subscription_updated",
                    details=f"status={status}",
                )

        elif event_type == "customer.subscription.deleted":
            subscription_id = data["id"]

            business = (
                db.query(Business)
                .filter(Business.stripe_subscription_id == subscription_id)
                .first()
            )

            if business:
                business.is_active = False
                business.tier = "foundation"
                business.stripe_subscription_status = "cancelled"
                business.stripe_current_period_end = None
                business.stripe_subscription_id = None

                db.commit()

                log_action(
                    db=db,
                    actor_type="system",
                    actor_id=business.id,
                    action="billing.subscription_cancelled",
                )

    finally:
        db.close()

    return {"received": True}

