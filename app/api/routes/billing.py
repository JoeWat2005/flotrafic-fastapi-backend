from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import stripe
from datetime import timezone

from app.db.session import get_db
from app.db.models import Business
from app.api.deps import get_current_business
from app.services.audit import log_action
from app.core.config import settings, apply_subscription_state
from app.core.utils import _safe_stripe_subscription_refresh

router = APIRouter(
    prefix="/billing",
    tags=["Billing"],
    dependencies=[Depends(get_current_business)],
)


"""
BILLING ROUTES => STRIPE SUBSCRIPTIONS & CUSTOMER PORTAL

Allows businesses to start checkout, view billing status,
and manage subscriptions via Stripe’s billing portal.
"""


#Create a Stripe checkout session for upgrading to the pro plan
@router.post("/checkout")
def create_checkout(
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    if business.tier == "pro":
        raise HTTPException(400, "Already on Pro")

    price_id = settings.STRIPE_PRO_PRICE_ID
    if not price_id:
        raise HTTPException(500, "Pro price not configured")

    if not business.stripe_customer_id:
        customer = stripe.Customer.create(
            email=business.email,
            name=business.name,
        )
        business.stripe_customer_id = customer.id
        db.commit()

    session = stripe.checkout.Session.create(
        customer=business.stripe_customer_id,
        mode="subscription",
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        metadata={
            "business_id": str(business.id),
            "tier": "pro",
        },
        success_url=f"{settings.FRONTEND_URL}/{business.slug}/dashboard?billing=success",
        cancel_url=f"{settings.FRONTEND_URL}/{business.slug}/dashboard?billing=cancel",
    )

    log_action(
        db=db,
        actor_type="business",
        actor_id=business.id,
        action="billing.checkout_started",
        details="tier=pro",
    )

    return {"checkout_url": session.url}


#Return current billing and subscription status for the business
@router.get("/overview")
def billing_overview(
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    _safe_stripe_subscription_refresh(business)

    apply_subscription_state(
        business,
        business.stripe_subscription_status,
    )
    db.commit()

    return {
        "tier": business.tier,
        "subscription_status": business.stripe_subscription_status,
        "current_period_end": (
            business.stripe_current_period_end.astimezone(timezone.utc).isoformat()
            if business.stripe_current_period_end
            else None
        ),
        "cancel_at_period_end": business.stripe_cancel_at_period_end,
        "grace_period_ends_at": (
            business.grace_period_ends_at.astimezone(timezone.utc).isoformat()
            if business.grace_period_ends_at
            else None
        ),
        "is_active": business.is_active,
        "email_verified": business.email_verified,
    }



#Launch the Stripe customer billing portal for subscription management
@router.post("/portal")
def billing_portal(
    business: Business = Depends(get_current_business),
):
    if not business.stripe_customer_id:
        raise HTTPException(400, "No Stripe customer")

    session = stripe.billing_portal.Session.create(
        customer=business.stripe_customer_id,
        return_url=f"https://yourdomain.co.uk/{business.slug}/dashboard/billing",
    )

    return {"url": session.url}

@router.post("/cancel")
def cancel_subscription(
    business: Business = Depends(get_current_business),
):
    if not business.stripe_subscription_id:
        raise HTTPException(400, "No active subscription")

    stripe.Subscription.modify(
        business.stripe_subscription_id,
        cancel_at_period_end=True,
    )

    return {"status": "cancelled_at_period_end"}
