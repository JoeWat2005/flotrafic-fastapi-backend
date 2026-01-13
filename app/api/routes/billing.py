from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import stripe
from datetime import timezone


from app.db.session import get_db
from app.db.models import Business
from app.api.deps import get_current_business
from app.core import stripe as stripe_config
from app.services.audit import log_action

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.post("/checkout")
def create_checkout(
    tier: str | None = None,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    """
    Creates a checkout session that ALWAYS includes:
    - Platform & maintenance (£10/month)
    - Optional managed OR autopilot tier
    - Optional one-time setup fee (first checkout only)
    """

    line_items = []

    # Determine Price ID based on tier (Single Price ID Model)
    selected_tier = tier if tier else "foundation"
    
    if selected_tier == "foundation":
        price_id = stripe_config.FOUNDATION_PRICE_ID
    elif selected_tier == "managed":
        price_id = stripe_config.MANAGED_PRICE_ID
    elif selected_tier == "autopilot":
        price_id = stripe_config.AUTOPILOT_PRICE_ID
    else:
        raise HTTPException(status_code=400, detail="Invalid tier")

    # Add the main subscription item
    line_items.append({"price": price_id, "quantity": 1})

    # One-time setup fee (only if never paid before)
    if not business.stripe_subscription_id and stripe_config.SETUP_PRICE_ID:
        line_items.append(
            {"price": stripe_config.SETUP_PRICE_ID, "quantity": 1}
        )

    # Create Stripe customer if needed
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
        line_items=line_items,
        success_url="https://yourdomain.co.uk/dashboard?billing=success",
        cancel_url="https://yourdomain.co.uk/dashboard?billing=cancel",
        metadata={
            "business_id": str(business.id),
            "tier": tier or "foundation",
        },
    )

    log_action(
        db=db,
        actor_type="business",
        actor_id=business.id,
        action="billing.checkout_started",
        details=f"tier={tier or 'foundation'}",
    )

    return {"checkout_url": session.url}

@router.get("/overview")
def billing_overview(
    db: Session = Depends(get_db),
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

@router.post("/portal")
def billing_portal(
    business: Business = Depends(get_current_business),
):
    if not business.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No Stripe customer")

    session = stripe.billing_portal.Session.create(
        customer=business.stripe_customer_id,
        return_url="https://yourdomain.co.uk/dashboard/billing",
    )

    return {"url": session.url}