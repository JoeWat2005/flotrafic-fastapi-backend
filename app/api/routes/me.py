from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_business
from app.db.session import get_db
from app.db.models import Business
from app.schemas.me import UpdateMe
from app.services.audit import log_action

router = APIRouter(
    prefix="/me",
    tags=["Me"],
    dependencies=[Depends(get_current_business)],
)

"""
ENQUIRIES ROUTES => REQUIRE BUSINESS AUTH
"""

#get me info
@router.get("/")
def get_me(
    business: Business = Depends(get_current_business),
):
    return {
        "id": business.id,
        "name": business.name,
        "email": business.email,
        "tier": business.tier,
        "is_active": business.is_active,
        "slug": business.slug,
    }

#get billing info
@router.get("/billing")
def get_billing(
    business: Business = Depends(get_current_business),
):
    return {
        "tier": business.tier,
        "is_active": business.is_active,
        "subscription_status": business.stripe_subscription_status,
        "current_period_end": business.stripe_current_period_end,
        "stripe_customer_id": business.stripe_customer_id,
        "stripe_subscription_id": business.stripe_subscription_id,
    }

#update profile
@router.patch("/")
def update_me(
    payload: UpdateMe,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    name = payload.name.strip()

    if not name:
        raise HTTPException(400, "Name cannot be empty")

    business.name = name
    db.commit()

    log_action(
        db=db,
        actor_type="business",
        actor_id=business.id,
        action="account.name_updated",
    )

    return {
        "id": business.id,
        "name": business.name,
        "email": business.email,
        "tier": business.tier,
        "is_active": business.is_active,
    }