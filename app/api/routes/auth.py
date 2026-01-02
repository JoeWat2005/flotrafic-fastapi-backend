from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Business
from app.core.security import verify_password
from app.core.jwt import create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    business = (
        db.query(Business)
        .filter(Business.name == form_data.username)
        .first()
    )

    if not business or not verify_password(
        form_data.password,
        business.hashed_password,
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(
        {
            "sub": str(business.id),  # ✅ MUST be string
            "tier": business.tier,
        }
    )

    return {
        "access_token": token,
        "token_type": "bearer",
    }


