from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_business
from app.db.session import get_db
from app.db.models import Business
from app.schemas.me import MeOut, BillingOut, UpdateMe
from app.services.audit import log_action

router = APIRouter(
    prefix="/me",
    tags=["Me"],
    dependencies=[Depends(get_current_business)],
)

"""
ME ROUTES => REQUIRE BUSINESS AUTH
"""

#get business info
@router.get("/", response_model=MeOut)
def get_me(
    business: Business = Depends(get_current_business),
):
    return business

#get business billing info
@router.get("/billing", response_model=BillingOut)
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

#update business name
@router.patch("/", response_model=MeOut)
def update_me(
    payload: UpdateMe,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    business.name = payload.name.strip()
    db.commit()

    log_action(
        db=db,
        actor_type="business",
        actor_id=business.id,
        action="account.name_updated",
    )

    return business