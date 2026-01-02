from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session
import stripe
import os

from app.db.session import SessionLocal
from app.db.models import Business

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
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            business_id = int(session["metadata"]["business_id"])
            tier = session["metadata"]["tier"]

            business = db.query(Business).get(business_id)
            if business:
                business.tier = tier
                business.stripe_subscription_id = session["subscription"]
                db.commit()

        elif event["type"] == "customer.subscription.deleted":
            sub = event["data"]["object"]
            business = (
                db.query(Business)
                .filter(Business.stripe_subscription_id == sub["id"])
                .first()
            )
            if business:
                business.tier = "foundation"
                business.stripe_subscription_id = None
                db.commit()

    finally:
        db.close()

    return {"received": True}
