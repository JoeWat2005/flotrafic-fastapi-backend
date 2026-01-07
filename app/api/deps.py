from jose import jwt, JWTError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from app.db.session import get_db
from app.db.models import Business, Admin
from app.core.jwt import SECRET_KEY, ALGORITHM
from app.core.tiers import TIERS

bearer_scheme = HTTPBearer()

# Grace period for billing issues (past_due/unpaid etc.)
GRACE_DAYS = 7


def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# =========================
# 🏢 Business auth (HARD LOCK + GRACE)
# =========================
def get_current_business(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Business:
    token = creds.credentials
    payload = decode_token(token)

    # 🚫 Admin tokens not allowed
    if payload.get("type") == "admin":
        raise HTTPException(status_code=403, detail="Admin token not allowed")

    business_id = payload.get("sub")
    if not business_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    business = db.query(Business).get(int(business_id))
    if not business:
        raise HTTPException(status_code=401, detail="Business not found")

    # 🚫 SUSPENSION LOCK (allow grace period)
    if not business.is_active:
        # If we have a known billing period end, allow a short grace window
        if business.stripe_current_period_end:
            now = datetime.now(timezone.utc)
            grace_until = business.stripe_current_period_end + timedelta(days=GRACE_DAYS)
            if now <= grace_until:
                return business

        raise HTTPException(
            status_code=403,
            detail="Business account is suspended",
        )

    return business


# =========================
# 🔒 Admin auth (unchanged)
# =========================
def get_current_admin(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Admin:
    token = creds.credentials
    payload = decode_token(token)

    if payload.get("type") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    admin_id = payload.get("sub")
    if not admin_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    admin = db.query(Admin).get(int(admin_id))
    if not admin:
        raise HTTPException(status_code=401, detail="Admin not found")

    return admin


# =========================
# 🧱 Tier feature enforcement
# =========================
def require_feature(feature: str):
    def _check(business: Business = Depends(get_current_business)):

        # 🔵 FEATURE TIER CHECK
        allowed = TIERS.get(business.tier, {}).get(feature, False)
        if not allowed:
            raise HTTPException(
                status_code=403,
                detail="Upgrade required",
            )

        # 🟣 PAID TIER BILLING CHECK
        if business.tier != "foundation":
            if business.stripe_subscription_status not in ("active", "trialing"):
                raise HTTPException(
                    status_code=402,
                    detail="Subscription payment required",
                )

            if business.stripe_current_period_end:
                now = datetime.now(timezone.utc)

                period_end = business.stripe_current_period_end
                if period_end.tzinfo is None:
                    period_end = period_end.replace(tzinfo=timezone.utc)

                    if now > period_end:
                        raise HTTPException(
                        status_code=402,
                        detail="Subscription expired",
                    )


        return business

    return _check