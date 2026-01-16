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
from app.schemas.auth import LoginRequest, PreRegisterRequest, TokenResponse, VerifyEmailCodeRequest, PasswordResetRequest, PasswordResetConfirmRequest

stripe.api_key = settings.STRIPE_SECRET_KEY

router = APIRouter(prefix="/auth", tags=["auth"])


"""
AUTH ROUTES => BUSINESS AUTHENTICATION & ACCOUNT LIFECYCLE

Handles login, pre-registration, email verification, Stripe checkout,
password resets, and all rate-limited auth-related actions.
"""


#Authenticate an existing business and return a JWT access token
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


#Pre-register a new business and send an email verification code
@router.post("/pre-register")
def pre_register(
    payload: PreRegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    print("\n=== PRE-REGISTER HIT ===")

    email = payload.email.lower().strip()
    name = payload.name.strip()

    print("Email:", email)
    print("Name:", name)
    print("Requested tier:", payload.tier)

    ip = request.client.host if request.client else "unknown"
    print("IP:", ip)

    key = f"auth:pre-register:{ip}:{email}"
    print("Rate limit key:", key)

    limit, window = RATE_LIMITS["pre_register"]
    print("Rate limit:", limit, "Window:", window)

    # 1️⃣ Rate limiting
    if not rate_limit(key, limit, window):
        print("❌ RATE LIMIT HIT")
        raise HTTPException(
            status_code=429,
            detail="Too many registration attempts. Please wait.",
        )

    # 2️⃣ Generate verification code
    code, expires = generate_verification_code()
    print("Generated verification code:", code)
    print("Verification expires at:", expires, "tzinfo:", expires.tzinfo if expires else None)

    # 3️⃣ Check existing business
    existing = db.query(Business).filter(Business.email == email).first()
    print("Existing business found:", bool(existing))

    # Safe retry for unverified emails
    if existing:
        print("Existing business ID:", existing.id)
        print("Email verified:", existing.email_verified)

        if existing.email_verified:
            print("❌ EMAIL ALREADY VERIFIED")
            raise HTTPException(
                status_code=400,
                detail="An account with this email already exists",
            )

        print("🔁 Resending verification code")

        existing.hashed_password = hash_password(payload.password)
        existing.tier = payload.tier
        existing.email_verification_code = code
        existing.email_verification_expires = expires
        existing.is_active = False
        existing.email_verified = False

        db.commit()
        print("DB commit complete (existing business updated)")

        print("➡️ Sending verification email (resend)")
        send_verification_email(user_email=existing.email, code=code)

        print("=== PRE-REGISTER COMPLETE (code_resent) ===")
        return {"status": "code_resent"}

    # 4️⃣ New account flow
    print("🆕 Creating new business")

    slug = slugify(name)
    print("Generated slug:", slug)

    if not slug:
        print("❌ INVALID BUSINESS NAME (slug empty)")
        raise HTTPException(
            status_code=400,
            detail="Business name must contain letters or numbers",
        )

    if slug in RESERVED_SLUGS:
        print("❌ RESERVED SLUG:", slug)
        raise HTTPException(
            status_code=400,
            detail="This business name is reserved",
        )

    slug_exists = db.query(Business).filter(Business.slug == slug).first()
    print("Slug already exists:", bool(slug_exists))

    if slug_exists:
        print("❌ SLUG CONFLICT")
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

    print("✅ New business created")
    print("Business ID:", business.id)

    print("➡️ Sending verification email (new account)")
    send_verification_email(user_email=business.email, code=code)

    print("=== PRE-REGISTER COMPLETE (code_sent) ===")

    return {"status": "code_sent"}



#Verify an email address using a one-time verification code
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
    
    if expires and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

    if not expires or expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Verification code expired")

    if business.email_verification_code != code:
        raise HTTPException(status_code=400, detail="Invalid verification code")

    business.email_verified = True
    business.email_verification_code = None
    business.email_verification_expires = None

    if business.tier == "free":
        business.is_active = True

    db.commit()

    log_action(
        db=db,
        actor_type="business",
        actor_id=business.id,
        action="auth.email_verified",
    )

    return {"status": "verified"}


#Start Stripe checkout flow for upgrading from free to pro
@router.post("/start-checkout")
def start_checkout(
    business: Business = Depends(get_current_business_onboarding),
):
    print("=== START CHECKOUT HIT ===")
    print("Business ID:", business.id)
    print("Business email:", business.email)
    print("Business tier:", business.tier)
    print("Business slug:", business.slug)

    # 1️⃣ Tier check
    if business.tier != "free":
        print("❌ BLOCKED: Business is not on free tier")
        raise HTTPException(status_code=400, detail="Already on paid plan")

    # 2️⃣ Price ID
    price_id = settings.STRIPE_PRO_PRICE_ID
    print("Stripe PRO price ID:", price_id)

    if not price_id:
        print("❌ ERROR: STRIPE_PRO_PRICE_ID is missing")
        raise HTTPException(status_code=500, detail="Pro price not configured")

    success_url = f"{settings.FRONTEND_URL}/{business.slug}/dashboard"
    cancel_url = success_url

    print("Success URL:", success_url)
    print("Cancel URL:", cancel_url)

    # 3️⃣ Stripe call
    try:
        print("➡️ Creating Stripe checkout session...")

        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            customer_email=business.email,
            line_items=[{"price": price_id, "quantity": 1}],
            metadata={
                "business_id": str(business.id),
                "tier": "pro",
            },
            success_url=success_url,
            cancel_url=cancel_url,
            idempotency_key=f"checkout:{business.id}:pro",
        )

        print("✅ Stripe session created")
        print("Session ID:", session.id)
        print("Session URL:", session.url)

    except Exception as e:
        print("❌ STRIPE ERROR")
        print(type(e))
        print(str(e))
        raise HTTPException(status_code=500, detail="Stripe checkout failed")

    # 4️⃣ Final sanity check
    if not session or not session.url:
        print("❌ ERROR: Session or session.url missing")
        raise HTTPException(status_code=500, detail="Checkout session invalid")

    print("=== CHECKOUT SUCCESS ===")

    return {"checkout_url": session.url}


#Resend email verification code
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


#Request a password reset email using a one-time code
@router.post("/request-password-reset")
def request_password_reset(
    payload: PasswordResetRequest,
    db: Session = Depends(get_db),
):
    email = payload.email.lower().strip()
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


#Reset account password after successful email + captcha verification
@router.post("/reset-password")
def reset_password(
    payload: PasswordResetConfirmRequest,
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
    
    if expires and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

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
