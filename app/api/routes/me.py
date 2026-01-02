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


# =========================
# GET /me
# =========================
@router.get("/")
def get_me(
    business: Business = Depends(get_current_business),
):
    return {
        "id": business.id,
        "name": business.name,
        "email": business.email,
        "tier": business.tier,
    }


# =========================
# PATCH /me
# =========================
@router.patch("/")
def update_me(
    payload: UpdateMe,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    business.name = payload.name
    db.commit()
    db.refresh(business)

    return {
        "id": business.id,
        "name": business.name,
        "email": business.email,
        "tier": business.tier,
    }


# =========================
# POST /me/change-password
# =========================
@router.post("/change-password")
def change_password(
    payload: ChangePassword,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    if not verify_password(payload.old_password, business.hashed_password):
        raise HTTPException(status_code=400, detail="Old password is incorrect")

    business.hashed_password = hash_password(payload.new_password)
    db.commit()

    return {"success": True}

