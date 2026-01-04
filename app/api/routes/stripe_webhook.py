from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session
import stripe
import os
from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.db.models import Business
from app.services.audit import log_action

router = APIRouter(prefix="/stripe", tags=["Stripe"])

# =========================
# STRIPE CONFIG (REQUIRED)
# =========================
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

if not WEBHOOK_SECRET:
    raise RuntimeError("STRIPE_WEBHOOK_SECRET is not set")


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
        event_type = event["type"]
        data = event["data"]["object"]

        # =========================
        # ACCOUNT CREATION
        # =========================
        if event_type == "checkout.session.completed":
            metadata = data.get("metadata") or {}

            email = metadata.get("email")
            if not email:
                return {"ignored": True}

            existing = (
                db.query(Business)
                .filter(Business.email == email)
                .first()
            )
            if existing:
                return {"already_exists": True}

            business = Business(
                name=metadata["name"],
                email=email,
                hashed_password=metadata["password_hash"],
                tier=metadata["tier"],
                stripe_customer_id=data.get("customer"),
                stripe_subscription_id=data.get("subscription"),
                stripe_subscription_status="active",
                stripe_current_period_end=datetime.now(timezone.utc),
                is_active=True,
            )

            db.add(business)
            db.commit()

            log_action(
                db=db,
                actor_type="system",
                actor_id=business.id,
                action="business.created_after_payment",
                details=f"tier={business.tier}",
            )

        # =========================
        # SUBSCRIPTION UPDATES
        # =========================
        elif event_type in (
            "customer.subscription.updated",
            "customer.subscription.deleted",
        ):
            subscription_id = data.get("id")
            status = data.get("status")

            if not subscription_id:
                return {"ignored": True}

            business = (
                db.query(Business)
                .filter(Business.stripe_subscription_id == subscription_id)
                .first()
            )

            if business:
                business.stripe_subscription_status = status
                business.is_active = status in ("active", "trialing")
                db.commit()

    finally:
        db.close()

    return {"received": True}