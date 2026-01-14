from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import stripe
from datetime import timezone

from app.db.session import get_db
from app.db.models import Business
from app.api.deps import get_current_business
from app.core import stripe as stripe_config
from app.services.audit import log_action

router = APIRouter(
    prefix="/billing",
    tags=["Billing"],
    dependencies=[Depends(get_current_business)],
)

"""
BILLING ROUTES => REQUIRE BUSINESS AUTH
"""

#launch stripe checkout
@router.post("/checkout")
def create_checkout(
    tier: str | None = None,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    selected_tier = tier or "foundation"

    tier_prices = {
        "pro": stripe_config.PRO_PRICE_ID,
    }

    price_id = tier_prices.get(selected_tier)
    if not price_id:
        raise HTTPException(400, "Invalid tier")

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
            "tier": selected_tier,
        },
        success_url=f"https://yourdomain.co.uk/{business.slug}/dashboard?billing=success",
        cancel_url=f"https://yourdomain.co.uk/{business.slug}/dashboard?billing=cancel",
    )

    log_action(
        db=db,
        actor_type="business",
        actor_id=business.id,
        action="billing.checkout_started",
        details=f"tier={selected_tier}",
    )

    return {"checkout_url": session.url}

#get billing overview
@router.get("/overview")
def billing_overview(
    business: Business = Depends(get_current_business),
):
    return {
        "tier": business.tier,
        "subscription_status": business.stripe_subscription_status,
        "current_period_end": (
            business.stripe_current_period_end.astimezone(timezone.utc).isoformat()
            if business.stripe_current_period_end
            else None
        ),
        "is_active": business.is_active,
    }

#launch stripe portal
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