from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import stripe

from app.db.session import get_db
from app.db.models import Business
from app.core.security import verify_password, hash_password
from app.core.jwt import create_access_token
from app.core import stripe as stripe_config
from app.services.audit import log_action

router = APIRouter(prefix="/auth", tags=["Auth"])

stripe.api_key = stripe_config.stripe.api_key


# =========================
# POST /auth/login (UNCHANGED)
# =========================
@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    business = (
        db.query(Business)
        .filter(Business.email == form_data.username)
        .first()
    )

    if not business or not verify_password(
        form_data.password,
        business.hashed_password,
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not business.is_active:
        raise HTTPException(
            status_code=403,
            detail="Business account is suspended",
        )

    token = create_access_token(
        {"sub": str(business.id), "tier": business.tier}
    )

    return {"access_token": token, "token_type": "bearer"}


# =========================
# POST /auth/pre-register
# =========================
@router.post("/pre-register")
def pre_register(
    name: str,
    email: str,
    password: str,
    tier: str,
):
    if tier not in {"foundation", "managed", "autopilot"}:
        raise HTTPException(status_code=400, detail="Invalid tier")

    tier_price_map = {
        "foundation": stripe_config.FOUNDATION_PRICE_ID,
        "managed": stripe_config.MANAGED_PRICE_ID,
        "autopilot": stripe_config.AUTOPILOT_PRICE_ID,
    }

    session = stripe.checkout.Session.create(
        mode="subscription",
        payment_method_types=["card"],
        line_items=[
            {"price": tier_price_map[tier], "quantity": 1},
            {"price": stripe_config.SETUP_PRICE_ID, "quantity": 1},
        ],
        metadata={
            "name": name,
            "email": email,
            "tier": tier,
            "password_hash": hash_password(password),
        },
        success_url="http://localhost:5173/success",
        cancel_url="http://localhost:5173/cancel",
    )

    return {"checkout_url": session.url}

