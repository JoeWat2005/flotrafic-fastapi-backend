from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Business
from app.db.session import get_db
from app.core.config import RESERVED_SLUGS

router = APIRouter(
    prefix="/public",
    tags=["Public"],  # ✅ MUST be a list
)


@router.get("/business")
def get_public_business(
    slug: str,
    db: Session = Depends(get_db),
):
    if slug in RESERVED_SLUGS:
        raise HTTPException(status_code=404, detail="Business not found")

    business = (
        db.query(Business)
        .filter(Business.slug == slug)
        .first()
    )

    if not business or not business.is_active:
        raise HTTPException(status_code=404, detail="Business not found")

    return {
        "name": business.name,
    }
