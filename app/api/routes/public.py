from fastapi import APIRouter, Depends, HTTPException
from app.api.routes import public
from app.db.models import Business
from sqlalchemy.orm import Session
from app.db.session import get_db

router = APIRouter(
    prefix="/public",
    tags="Public",
)

@router.get("/business")
def get_public_business(
    slug: str,
    db: Session = Depends(get_db),
):
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
