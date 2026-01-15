from jose import jwt, JWTError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.db.session import get_db
from app.db.models import Business, Admin
from app.core.security import SECRET_KEY, ALGORITHM
from app.core.config import TIERS


#HTTP bearer scheme used for JWT-based authentication
bearer_scheme = HTTPBearer(auto_error=False)


#Decode and validate a JWT access token
def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        exp = payload.get("exp")
        if exp is not None:
            if datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
                raise HTTPException(status_code=401, detail="Token expired")

        return payload

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


#Resolve the currently authenticated business with full access checks
def get_current_business(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Business:

    if not creds or not creds.credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

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


#Resolve an authenticated business during onboarding before full activation
def get_current_business_onboarding(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Business:

    if not creds or not creds.credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

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


#Resolve the currently authenticated administrator
def get_current_admin(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Admin:

    if not creds or not creds.credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

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


#Enforce feature availability and subscription validity for a business
def require_feature(feature: str):
    def _check(business: Business = Depends(get_current_business)):

        if not TIERS.get(business.tier, {}).get(feature):
            raise HTTPException(status_code=403, detail="Upgrade required")

        if business.tier != "free":
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