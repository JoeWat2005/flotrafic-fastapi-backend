from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import timezone

from app.db.session import get_db
from app.db.models import Business
from app.api.deps import get_current_business

router = APIRouter(
    prefix="/billing",
    tags=["Billing"],
    dependencies=[Depends(get_current_business)],
)


"""
BILLING ROUTES => SIMPLIFIED FOR BETA

Pro plan is disabled for now. Only returns basic billing overview.
Full Stripe integration will be implemented later.
"""


# Return current billing and subscription status for the business
@router.get("/overview")
def billing_overview(
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """
    Returns simplified billing overview.
    Pro features are disabled during beta.
    """
    
    return {
        "tier": business.tier,
        "has_pro_access": False,  # Pro is disabled for now
        "access_expires_at": None,
        "is_cancelled": False,
        "is_active": business.is_active,
        "email_verified": business.email_verified,
    }


# Disabled - Pro plan checkout (to be implemented later)
@router.post("/checkout")
def create_checkout(
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """
    Pro plan checkout is currently disabled.
    Will be enabled when Pro features are ready.
    """
    raise HTTPException(
        status_code=503,
        detail="Pro plan is coming soon. Stay tuned!"
    )


# Disabled - Stripe billing portal (to be implemented later)
@router.post("/portal")
def billing_portal(
    business: Business = Depends(get_current_business),
):
    """
    Billing portal is currently disabled.
    Will be enabled when Pro features are ready.
    """
    raise HTTPException(
        status_code=503,
        detail="Billing portal is coming soon. Stay tuned!"
    )


# Disabled - Cancel subscription (to be implemented later)
@router.post("/cancel")
def cancel_subscription(
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """
    Subscription cancellation is currently disabled.
    Will be enabled when Pro features are ready.
    """
    raise HTTPException(
        status_code=503,
        detail="Subscription management is coming soon. Stay tuned!"
    )


# Disabled - Resume subscription (to be implemented later)
@router.post("/resume")
def resume_subscription(
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """
    Subscription resumption is currently disabled.
    Will be enabled when Pro features are ready.
    """
    raise HTTPException(
        status_code=503,
        detail="Subscription management is coming soon. Stay tuned!"
    )