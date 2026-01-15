from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
import stripe

from app.db.session import get_db
from app.db.models import Business
from app.core.security import hash_password, verify_password, create_access_token, verify_captcha, rate_limit
from app.services.email import (
    send_verification_email,
    send_password_reset_email,
)
from app.core.utils import slugify, generate_verification_code
from app.api.deps import get_current_business_onboarding
from app.core.config import settings, RESERVED_SLUGS, RATE_LIMITS
from app.services.audit import log_action
from app.schemas.auth import LoginRequest, PreRegisterRequest, ResetPasswordRequest, TokenResponse, VerifyEmailCodeRequest

stripe.api_key = settings.STRIPE_SECRET_KEY

router = APIRouter(prefix="/auth", tags=["auth"])

"""
AUTH ROUTES => AUTHENICATION

1) AUTH/LOGIN => RATE LIMIT OF 5 REQUESTS / IP / 1 MINUTE
2) AUTH/PRE-REGISTER => RATE LIMIT OF 3 REQUESTS / IP / 1 MINUTE
3) AUTH/VERIFY-EMAIL-CODE => RATE LIMIT OF 5 REQUESTS / IP / 1 MINUTE
4) AUTH/START-CHECKOUT => NO RATE LIMIT, PROTECTED BY "get_current_business_onboarding"
5) AUTH/RESEND-VERIFICATION => RATE LIMIT OF 2 REQUESTS / EMAIL / 1 MINUTE
6) AUTH/REQUEST-PASSWORD-RESET => RATE LIMIT OF 2 REQUESTS / EMAIL / 1 MINUTE
7) AUTH/RESET-PASSWORD => RATE LIMIT OF 5 REQUESTS / IP / 1 MINUTE
""" 

#business login
@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    email = payload.username.lower().strip()
    password = payload.password

    ip = request.client.host if request.client else "unknown"
    key = f"auth:login:{ip}:{email}"

    limit, window = RATE_LIMITS["login"]
    if not rate_limit(key, limit, window):
        raise HTTPException(status_code=429, detail="Too many login attempts")

    business = db.query(Business).filter(Business.email == email).first()

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

    business.password_reset_code = None
    business.password_reset_expires = None
    db.commit()

    log_action(db=db, actor_type="business", actor_id=business.id, action="auth.login")

    token = create_access_token({"sub": str(business.id)})
    return TokenResponse(access_token=token)


#business pre-register
@router.post("/pre-register")
def pre_register(
    payload: PreRegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    email = payload.email.lower().strip()
    name = payload.name.strip()

    ip = request.client.host if request.client else "unknown"
    key = f"auth:pre-register:{ip}:{email}"

    limit, window = RATE_LIMITS["pre_register"]
    if not rate_limit(key, limit, window):
        raise HTTPException(
            status_code=429,
            detail="Too many registration attempts. Please wait.",
        )

    code, expires = generate_verification_code()

    existing = db.query(Business).filter(Business.email == email).first()

    # Safe retry for unverified emails
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

        send_verification_email(user_email=existing.email, code=code)
        return {"status": "code_resent"}

    # New account creation
    slug = slugify(name)

    if not slug:
        raise HTTPException(
            status_code=400,
            detail="Business name must contain letters or numbers",
        )

    if slug in RESERVED_SLUGS:
        raise HTTPException(
            status_code=400,
            detail="This business name is reserved",
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

    send_verification_email(user_email=business.email, code=code)
    return {"status": "code_sent"}

#verify email verification code
@router.post("/verify-email-code")
def verify_email_code(
    payload: VerifyEmailCodeRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    email = payload.email.lower().strip()
    code = payload.code.strip()

    ip = request.client.host if request.client else "unknown"
    key = f"auth:verify-email-code:{ip}:{email}"

    limit, window = RATE_LIMITS["verify_email"]
    if not rate_limit(key, limit, window):
        raise HTTPException(status_code=429, detail="Too many attempts")

    verify_captcha(payload.captcha_token)

    business = db.query(Business).filter(Business.email == email).first()
    if not business:
        raise HTTPException(status_code=400, detail="Invalid verification code")

    if business.email_verified:
        return {"status": "already_verified"}

    expires = business.email_verification_expires
    if not expires or expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Verification code expired")

    if business.email_verification_code != code:
        raise HTTPException(status_code=400, detail="Invalid verification code")

    business.email_verified = True
    business.email_verification_code = None
    business.email_verification_expires = None

    if business.tier == "free":
        business.is_active = True   # 🔧 FIXED (was ==)

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
    business: Business = Depends(get_current_business_onboarding),
):
    # Only free users should ever hit this
    if business.tier != "free":
        raise HTTPException(status_code=400, detail="Already on paid plan")

    price_id = settings.STRIPE_PRO_PRICE_ID
    if not price_id:
        raise HTTPException(status_code=500, detail="Pro price not configured")

    session = stripe.checkout.Session.create(
        mode="subscription",
        payment_method_types=["card"],
        customer_email=business.email,
        line_items=[{"price": price_id, "quantity": 1}],
        metadata={
            "business_id": str(business.id),
            "tier": "pro",
        },
        success_url=f"{settings.FRONTEND_URL}/{business.slug}/dashboard",
        cancel_url=f"{settings.FRONTEND_URL}/{business.slug}/dashboard",
        idempotency_key=f"checkout:{business.id}:pro",
    )

    return {"checkout_url": session.url}

#request resend verification
@router.post("/resend-verification")
def resend_verification(
    payload: dict,
    db: Session = Depends(get_db),
):
    email = (payload.get("email") or "").lower().strip()
    if not email:
        return {"status": "ok"}

    key = f"auth:resend-verification:{email}"
    limit, window = RATE_LIMITS["resend_verification"]
    if not rate_limit(key, limit, window):
        return {"status": "ok"}

    business = db.query(Business).filter(Business.email == email).first()
    if not business or business.email_verified:
        return {"status": "ok"}

    code, expires = generate_verification_code()

    business.email_verification_code = code
    business.email_verification_expires = expires
    business.is_active = False
    business.email_verified = False

    db.commit()

    send_verification_email(user_email=business.email, code=code)
    return {"status": "ok"}

#request reset password
@router.post("/request-password-reset")
def request_password_reset(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    email = (payload.get("email") or "").lower().strip()
    if not email:
        return {"status": "ok"}

    key = f"auth:request-password-reset:{email}"
    limit, window = RATE_LIMITS["request_password_reset"]
    if not rate_limit(key, limit, window):
        return {"status": "ok"}

    business = db.query(Business).filter(Business.email == email).first()
    if not business:
        return {"status": "ok"}

    code, expires = generate_verification_code()

    business.password_reset_code = code
    business.password_reset_expires = expires
    db.commit()

    send_password_reset_email(user_email=business.email, code=code)
    return {"status": "ok"}

#reset password
@router.post("/reset-password")
def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    email = payload.email.lower().strip()

    ip = request.client.host if request.client else "unknown"
    key = f"auth:reset-password:{ip}:{email}"

    limit, window = RATE_LIMITS["reset_password"]
    if not rate_limit(key, limit, window):
        raise HTTPException(status_code=429, detail="Too many attempts")

    verify_captcha(payload.captcha_token)

    business = db.query(Business).filter(Business.email == email).first()
    if not business:
        raise HTTPException(status_code=400, detail="Invalid reset code")

    expires = business.password_reset_expires
    if not expires or expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")

    if business.password_reset_code != payload.code:
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")

    business.hashed_password = hash_password(payload.new_password)
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
