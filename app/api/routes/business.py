from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.db.models import Business
from app.schemas.business import (
    BusinessOut,
    BusinessTierUpdate,
)
from app.api.deps import get_current_admin
from app.services.audit import log_action

router = APIRouter(
    prefix="/businesses",
    tags=["Businesses"],
    dependencies=[Depends(get_current_admin)],
)

"""
BUSINESS ROUTES => REQUIRE ADMIN AUTH
"""

#get businesses
@router.get("/", response_model=List[BusinessOut])
def list_businesses(
    db: Session = Depends(get_db),
):
    return db.query(Business).order_by(Business.id).all()

#update business tier
@router.patch("/{business_id}/tier", response_model=BusinessOut)
def update_business_tier(
    business_id: int,
    payload: BusinessTierUpdate,
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin),
):
    business = db.get(Business, business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    business.tier = payload.tier
    db.commit()

    log_action(
        db=db,
        actor_type="admin",
        actor_id=admin.id,
        action="business.tier_changed",
        details=f"business_id={business.id},tier={payload.tier}",
    )

    return business

#suspend business
@router.patch("/{business_id}/suspend", response_model=BusinessOut)
def suspend_business(
    business_id: int,
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin),
):
    business = db.get(Business, business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    business.is_active = False
    db.commit()

    log_action(
        db=db,
        actor_type="admin",
        actor_id=admin.id,
        action="business.suspended",
        details=f"business_id={business.id}",
    )

    return business

#activate business
@router.patch("/{business_id}/activate", response_model=BusinessOut)
def activate_business(
    business_id: int,
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin),
):
    business = db.get(Business, business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    business.is_active = True
    db.commit()

    log_action(
        db=db,
        actor_type="admin",
        actor_id=admin.id,
        action="business.activated",
        details=f"business_id={business.id}",
    )

    return business

#delete business
@router.delete("/{business_id}", response_model=dict)
def delete_business(
    business_id: int,
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin),
):
    business = db.get(Business, business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    db.delete(business)
    db.commit()

    log_action(
        db=db,
        actor_type="admin",
        actor_id=admin.id,
        action="business.deleted",
        details=f"business_id={business_id}",
    )

    return {"success": True}