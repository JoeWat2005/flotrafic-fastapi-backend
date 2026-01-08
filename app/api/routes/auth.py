from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import stripe

from app.db.session import get_db
from app.db.models import Business
from app.core.security import verify_password, hash_password
from app.core.jwt import create_access_token
from app.core import stripe as stripe_config
from app.schemas.auth import PreRegisterRequest
from app.core.captcha import verify_captcha

router = APIRouter(prefix="/auth", tags=["Auth"])
stripe.api_key = stripe_config.stripe.api_key


# =========================
# POST /auth/login
# =========================
@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    if not form_data.username or not form_data.password:
        raise HTTPException(
            status_code=400,
            detail="Email and password are required",
        )

    business = (
        db.query(Business)
        .filter(Business.email == form_data.username.lower())
        .first()
    )

    if not business or not verify_password(
        form_data.password,
        business.hashed_password,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

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
    payload: PreRegisterRequest,
    db: Session = Depends(get_db),
):
    # -------------------------
    # CAPTCHA
    # -------------------------
    verify_captcha(payload.captcha_token)

    # -------------------------
    # PASSWORD VALIDATION
    # -------------------------
    PreRegisterRequest.validate_password(payload.password)
    PreRegisterRequest.validate_confirm(
        payload.password,
        payload.confirm_password,
    )

    # -------------------------
    # DUPLICATE EMAIL CHECK
    # -------------------------
    existing_email = (
        db.query(Business)
        .filter(Business.email == payload.email.lower())
        .first()
    )
    if existing_email:
        raise HTTPException(
            status_code=400,
            detail="An account with this email already exists",
        )

    # -------------------------
    # DUPLICATE BUSINESS NAME CHECK
    # -------------------------
    existing_name = (
        db.query(Business)
        .filter(Business.name.ilike(payload.name.strip()))
        .first()
    )
    if existing_name:
        raise HTTPException(
            status_code=400,
            detail="A business with this name already exists",
        )

    # -------------------------
    # STRIPE PRICE MAP
    # -------------------------
    tier_price_map = {
        "foundation": stripe_config.FOUNDATION_PRICE_ID,
        "managed": stripe_config.MANAGED_PRICE_ID,
        "autopilot": stripe_config.AUTOPILOT_PRICE_ID,
    }

    if payload.tier not in tier_price_map:
        raise HTTPException(
            status_code=400,
            detail="Invalid subscription tier selected",
        )

    # -------------------------
    # CREATE STRIPE CHECKOUT
    # -------------------------
    session = stripe.checkout.Session.create(
        mode="subscription",
        payment_method_types=["card"],
        line_items=[
            {"price": tier_price_map[payload.tier], "quantity": 1},
            {"price": stripe_config.SETUP_PRICE_ID, "quantity": 1},
        ],
        metadata={
            "name": payload.name,
            "email": payload.email.lower(),
            "tier": payload.tier,
            "password_hash": hash_password(payload.password),
        },
        success_url="http://localhost:5173/?signup=success",
        cancel_url="http://localhost:5173/cancel",
    )

    return {"checkout_url": session.url}


