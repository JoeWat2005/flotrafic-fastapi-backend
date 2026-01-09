from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_business
from app.db.session import get_db
from app.db.models import Business
from app.core.security import verify_password, hash_password
from app.schemas.me import UpdateMe, ChangePassword

router = APIRouter(
    prefix="/me",
    tags=["Me"],
)


# -------------------------------------------------------------------
# GET /me
# - identity endpoint
# - no branching
# -------------------------------------------------------------------
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
    }


# -------------------------------------------------------------------
# GET /me/billing
# - informational only
# - no validation logic
# -------------------------------------------------------------------
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


# -------------------------------------------------------------------
# PATCH /me
# - frontend gates name validity
# - backend enforces ownership only
# -------------------------------------------------------------------
@router.patch("/")
def update_me(
    payload: UpdateMe,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    business.name = payload.name.strip()
    db.commit()

    return {
        "id": business.id,
        "name": business.name,
        "email": business.email,
        "tier": business.tier,
        "is_active": business.is_active,
    }


# -------------------------------------------------------------------
# POST /me/change-password
# - frontend gates password strength
# - backend enforces auth boundary
# -------------------------------------------------------------------
@router.post("/change-password")
def change_password(
    payload: ChangePassword,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    # Auth boundary: must know current password
    if not verify_password(payload.old_password, business.hashed_password):
        raise HTTPException(
            status_code=400,
            detail="Invalid credentials",
        )

    business.hashed_password = hash_password(payload.new_password)
    db.commit()

    return {"status": "ok"}
