from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.db.models import Business
from app.schemas.business import (
    BusinessCreate,
    BusinessOut,
    BusinessTierUpdate,
)
from app.api.deps import get_current_admin
from app.core.security import hash_password


# 🔒 ALL endpoints in this router are ADMIN-ONLY
router = APIRouter(
    prefix="/businesses",
    tags=["Businesses"],
    dependencies=[Depends(get_current_admin)],
)


# =========================
# CREATE business
# =========================
@router.post("/", response_model=BusinessOut)
def create_business(
    payload: BusinessCreate,
    db: Session = Depends(get_db),
):
    existing = (
        db.query(Business)
        .filter(Business.email == payload.email)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Business already exists")

    business = Business(
        name=payload.name,
        email=payload.email,
        tier=payload.tier,
        hashed_password=hash_password(payload.password),
    )

    db.add(business)
    db.commit()
    db.refresh(business)

    return business


# =========================
# LIST businesses
# =========================
@router.get("/", response_model=List[BusinessOut])
def list_businesses(
    db: Session = Depends(get_db),
):
    return db.query(Business).order_by(Business.id).all()


# =========================
# UPDATE business tier ⭐
# =========================
@router.patch("/{business_id}/tier", response_model=BusinessOut)
def update_business_tier(
    business_id: int,
    payload: BusinessTierUpdate,
    db: Session = Depends(get_db),
):
    business = db.query(Business).get(business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    business.tier = payload.tier
    db.commit()
    db.refresh(business)

    return business


# =========================
# DELETE business
# =========================
@router.delete("/{business_id}", response_model=dict)
def delete_business(
    business_id: int,
    db: Session = Depends(get_db),
):
    business = db.query(Business).get(business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    db.delete(business)
    db.commit()

    return {"success": True}


