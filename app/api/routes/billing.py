from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Business
from app.api.deps import get_current_business
from app.core import stripe as stripe_config
import stripe

router = APIRouter(
    prefix="/billing",
    tags=["Billing"],
)


@router.post("/checkout")
def create_checkout(
    tier: str,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    if tier not in ("managed", "autopilot"):
        raise HTTPException(status_code=400, detail="Invalid tier")

    price_id = (
        stripe_config.MANAGED_PRICE_ID
        if tier == "managed"
        else stripe_config.AUTOPILOT_PRICE_ID
    )

    # Create Stripe customer if missing
    if not business.stripe_customer_id:
        customer = stripe.Customer.create(
            email=business.email,
            name=business.name,
        )
        business.stripe_customer_id = customer.id
        db.commit()

    session = stripe.checkout.Session.create(
        customer=business.stripe_customer_id,
        payment_method_types=["card"],
        mode="subscription",
        line_items=[
            {"price": price_id, "quantity": 1}
        ],
        success_url="https://yourdomain.co.uk/dashboard?billing=success",
        cancel_url="https://yourdomain.co.uk/dashboard?billing=cancel",
        metadata={
            "business_id": str(business.id),
            "tier": tier,
        },
    )

    return {"checkout_url": session.url}
