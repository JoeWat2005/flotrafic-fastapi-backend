from datetime import datetime, timezone, timedelta
import secrets
import stripe

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Business
from app.schemas.auth import PreRegisterRequest
from app.core.security import hash_password, verify_password, create_access_token, verify_captcha, rate_limit
from app.services.email import (
    send_verification_email,
    send_password_reset_email,
)
from app.core.utils import slugify
from app.api.deps import get_current_business_onboarding
from app.core.config import settings, RESERVED_SLUGS
from app.services.audit import log_action

stripe.api_key = settings.STRIPE_SECRET_KEY

router = APIRouter(prefix="/auth", tags=["auth"])

"""
AUTH ROUTES => AUTHENICATION

1) AUTH/LOGIN => 
2) AUTH/PRE_REGISTER => 
""" 

#business login
@router.post("/login")
def login(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db)
):
    
    ip = request.client.host if request.client else "unknown"
    key = f"auth:login:{ip}"

    if not rate_limit(key, max_requests=5, window_seconds=60):
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Try again shortly.",
        )
    
    email = (payload.get("username") or "").lower().strip()
    password = payload.get("password") or ""

    business = (
        db.query(Business)
        .filter(Business.email == email)
        .first()
    )

    if not business or not verify_password(password, business.hashed_password):

        log_action(
            db=db,
            actor_type="business",
            actor_id=0,
            action="auth.login_failed",
            details=f"email={email}",
        )

        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not business.email_verified:
        raise HTTPException(status_code=403, detail="Email not verified")

    if business.password_reset_code:
        business.password_reset_code = None
        business.password_reset_expires = None
    
    db.commit()

    log_action(
            db=db,
            actor_type="business",
            actor_id=business.id,
            action="auth.login",
        )

    token = create_access_token({"sub": str(business.id)})
    

    return {
        "access_token": token,
        "token_type": "bearer",
    }

#business pre-register
@router.post("/pre-register")
def pre_register(
    payload: PreRegisterRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    
    ip = request.client.host if request.client else "unknown"
    key = f"auth:pre-register:{ip}"

    if not rate_limit(key, max_requests=3, window_seconds=60):
        raise HTTPException(
            status_code=429,
            detail="Too many registration attempts. Please wait.",
        )
    
    email = payload.email.lower().strip()
    name = payload.name.strip()

    #email verification code
    code = f"{secrets.randbelow(1_000_000):06d}"
    expires = datetime.now(timezone.utc) + timedelta(minutes=10)

    existing = db.query(Business).filter(Business.email == email).first()

    #safe retry for unverified emails
    if existing:
        if existing.email_verified:
            raise HTTPException(
                status_code=400,
                detail="An account with this email already exists",
            )

        existing.hashed_password = hash_password(payload.password)
        existing.tier = payload.tier
        existing.email_verification_code = code
        existing.email_verification_expires = expires
        existing.is_active = False
        existing.email_verified = False

        db.commit()

        send_verification_email(
            user_email=existing.email, 
            code=code
        )

        return {"status": "code_resent"}

    #new account creation
    slug = slugify(name)

    if not slug:
        raise HTTPException(
            status_code=400,
            detail="Business name must contain letters or numbers"
        )
    
    if slug in RESERVED_SLUGS:
        raise HTTPException(
            status_code=400,
            detail="This business name is reserved"
        )
    
    if db.query(Business).filter(Business.slug == slug).first():
        raise HTTPException(
            status_code=400,
            detail="A business with a similar name already exists",
        )

    business = Business(
        name=name,
        slug=slug,
        email=email,
        tier=payload.tier,
        hashed_password=hash_password(payload.password),
        is_active=False,
        email_verified=False,
        email_verification_code=code,
        email_verification_expires=expires,
    )

    db.add(business)
    db.commit()

    send_verification_email(
        user_email=business.email, 
        code=code
    )

    return {"status": "code_sent"}

#verify email verification code
@router.post("/verify-email-code")
def verify_email_code(
    payload: dict, 
    request: Request,
    db: Session = Depends(get_db)
):
    
    ip = request.client.host if request.client else "unknown"
    key = f"auth:verify-email:{ip}"

    if not rate_limit(key, max_requests=5, window_seconds=60):
        raise HTTPException(
            status_code=429,
            detail="Too many verification attempts. Please wait.",
        )
    
    captcha_token = payload.get("captcha_token")
    verify_captcha(captcha_token)

    email = (payload.get("email") or "").lower().strip()
    code = (payload.get("code") or "").strip()

    business = db.query(Business).filter(Business.email == email).first()

    if not business:
        raise HTTPException(status_code=400, detail="Invalid verification code")

    #already verified - don't error
    if business.email_verified:
        return {"status": "already_verified"}

    expires = business.email_verification_expires
    if not expires:
        raise HTTPException(status_code=400, detail="Invalid verification code")

    #protective timezone normalisation
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

    if expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Verification code expired")

    if business.email_verification_code != code:
        raise HTTPException(status_code=400, detail="Invalid verification code")

    #mark business as verified and invalidate code
    business.email_verified = True
    business.email_verification_code = None
    business.email_verification_expires = None

    db.commit()

    log_action(
        db=db,
        actor_type="business",
        actor_id=business.id,
        action="auth.email_verified",
    )

    return {"status": "verified"}

#launch stripe checkout
@router.post("/start-checkout")
def start_checkout(
    #not public
    business: Business = Depends(get_current_business_onboarding),
):
    
    if business.stripe_subscription_status in ("active", "trialing"):
        raise HTTPException(status_code=400, detail="Subscription already active")

    tier_prices = {
        "foundation": settings.STRIPE_FOUNDATION_PRICE_ID,
        "managed": settings.STRIPE_MANAGED_PRICE_ID,
        "autopilot": settings.STRIPE_AUTOPILOT_PRICE_ID,
    }

    price_id = tier_prices.get(business.tier)
    if not price_id:
        raise HTTPException(status_code=400, detail="Invalid tier")

    session = stripe.checkout.Session.create(
        mode="subscription",
        payment_method_types=["card"],
        customer_email=business.email,
        line_items=[
            {"price": price_id, "quantity": 1},
        ],
        metadata={
            "business_id": str(business.id),
            "tier": business.tier,
        },
        success_url=f"{settings.FRONTEND_URL}/{business.slug}/dashboard",
        cancel_url=f"{settings.FRONTEND_URL}/{business.slug}/dashboard",
        idempotency_key=f"checkout:{business.id}:{business.tier}",
    )

    return {"checkout_url": session.url}

#request resed verification
@router.post("/resend-verification")
def resend_verification(payload: dict, db: Session = Depends(get_db)):
    email = (payload.get("email") or "").lower().strip()

    if not email:
        return {"status": "ok"}

    business = db.query(Business).filter(Business.email == email).first()

    if not business or business.email_verified:
        return {"status": "ok"}

    code = f"{secrets.randbelow(1_000_000):06d}"
    expires = datetime.now(timezone.utc) + timedelta(minutes=10)

    business.email_verification_code = code
    business.email_verification_expires = expires
    business.is_active = False
    business.email_verified = False

    db.commit()

    send_verification_email(
        user_email=business.email, 
        code=code
    )

    return {"status": "ok"}


#request reset password
@router.post("/request-password-reset")
def request_password_reset(payload: dict, db: Session = Depends(get_db)):
    email = (payload.get("email") or "").lower().strip()

    if not email:
        return {"status": "ok"}

    business = db.query(Business).filter(Business.email == email).first()

    if not business:
        return {"status": "ok"}

    code = f"{secrets.randbelow(1_000_000):06d}"
    expires = datetime.now(timezone.utc) + timedelta(minutes=10)

    business.password_reset_code = code
    business.password_reset_expires = expires
    db.commit()

    send_password_reset_email(
        user_email=business.email,
        code=code,
    )


    return {"status": "ok"}


#reset password
@router.post("/reset-password")
def reset_password(payload: dict, db: Session = Depends(get_db)):
    email = (payload.get("email") or "").lower().strip()
    code = (payload.get("code") or "").strip()
    new_password = payload.get("new_password")
    captcha_token = payload.get("captcha_token")

    verify_captcha(captcha_token)

    business = db.query(Business).filter(Business.email == email).first()

    if not business:
        raise HTTPException(status_code=400, detail="Invalid reset code")

    expires = business.password_reset_expires
    if not expires:
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")

    # Defensive timezone normalisation
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

    if (
        business.password_reset_code != code
        or datetime.now(timezone.utc) > expires
    ):
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")

    business.hashed_password = hash_password(new_password)
    business.password_reset_code = None
    business.password_reset_expires = None

    db.commit()

    log_action(
        db=db,
        actor_type="business",
        actor_id=business.id,
        action="auth.password_reset",
    )

    return {"status": "ok"}

