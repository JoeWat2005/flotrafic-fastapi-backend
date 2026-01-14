from jose import jwt, JWTError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.db.session import get_db
from app.db.models import Business, Admin
from app.core.security import SECRET_KEY, ALGORITHM
from app.core.stripe import TIERS

bearer_scheme = HTTPBearer()


# -------------------------------------------------------------------
# TOKEN DECODE
# - single responsibility
# - no UX messaging
# -------------------------------------------------------------------
def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# -------------------------------------------------------------------
# STRICT BUSINESS AUTH
# - verified
# - active
# - NOT admin
# -------------------------------------------------------------------
def get_current_business(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Business:
    payload = decode_token(creds.credentials)

    if payload.get("type") == "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    business_id = payload.get("sub")
    if not business_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    business = db.get(Business, int(business_id))
    if not business:
        raise HTTPException(status_code=401, detail="Invalid token")

    if not business.email_verified:
        raise HTTPException(status_code=403, detail="Email not verified")

    if not business.is_active:
        raise HTTPException(status_code=403, detail="Account inactive")

    return business


# -------------------------------------------------------------------
# ONBOARDING BUSINESS AUTH
# - verified
# - NOT active yet
# - used ONLY for checkout / onboarding
# -------------------------------------------------------------------
def get_current_business_onboarding(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Business:
    payload = decode_token(creds.credentials)

    if payload.get("type") == "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    business_id = payload.get("sub")
    if not business_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    business = db.get(Business, int(business_id))
    if not business:
        raise HTTPException(status_code=401, detail="Invalid token")

    if not business.email_verified:
        raise HTTPException(status_code=403, detail="Email not verified")

    return business


# -------------------------------------------------------------------
# ADMIN AUTH
# - admin token only
# -------------------------------------------------------------------
def get_current_admin(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Admin:
    payload = decode_token(creds.credentials)

    if payload.get("type") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    admin_id = payload.get("sub")
    if not admin_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    admin = db.get(Admin, int(admin_id))
    if not admin:
        raise HTTPException(status_code=401, detail="Invalid token")

    return admin


# -------------------------------------------------------------------
# FEATURE / TIER ENFORCEMENT
# - depends on STRICT business auth
# - minimal error surface
# -------------------------------------------------------------------
def require_feature(feature: str):
    def _check(business: Business = Depends(get_current_business)):

        # -------------------------
        # FEATURE AVAILABILITY
        # -------------------------
        if not TIERS.get(business.tier, {}).get(feature):
            raise HTTPException(status_code=403, detail="Upgrade required")

        # -------------------------
        # BILLING ENFORCEMENT
        # (non-foundation only)
        # -------------------------
        if business.tier != "foundation":
            if business.stripe_subscription_status not in ("active", "trialing"):
                raise HTTPException(status_code=402, detail="Payment required")

            period_end = business.stripe_current_period_end
            if period_end:
                if period_end.tzinfo is None:
                    period_end = period_end.replace(tzinfo=timezone.utc)

                if datetime.now(timezone.utc) > period_end:
                    raise HTTPException(status_code=402, detail="Subscription expired")

        return business

    return _check

