from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Admin
from app.core.security import verify_password, create_access_token, rate_limit
from app.services.audit import log_action
from app.schemas.admin_auth import AdminLogin
from app.core.config import RATE_LIMITS

router = APIRouter(prefix="/admin/auth", tags=["Admin Auth"])

"""
ADMIN AUTH ROUTES => ADMIN-ONLY AUTHENTICATION

Provides email + password login for administrators with strict
IP-based rate limiting and full audit logging.
"""

#Authenticate an admin via email and password and issue an admin-scoped JWT
@router.post("/login")
def admin_login(
    payload: AdminLogin,
    request: Request,
    db: Session = Depends(get_db),
):
    email = payload.email.strip().lower()
    password = payload.password

    ip = request.client.host if request.client else "unknown"
    key = f"admin_login:{ip}:{email}"

    limit, window = RATE_LIMITS["login"]
    if not rate_limit(key, limit, window):
        raise HTTPException(status_code=429, detail="Too many login attempts")

    admin = (
        db.query(Admin)
        .filter(Admin.email == email)
        .first()
    )

    if not admin or not verify_password(password, admin.hashed_password):
        log_action(
            db=db,
            actor_type="admin",
            actor_id=0,
            action="admin.login_failed",
            details=f"email={email}",
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")

    log_action(
        db=db,
        actor_type="admin",
        actor_id=admin.id,
        action="admin.login_success",
    )

    token = create_access_token(
        {
            "sub": str(admin.id),
            "type": "admin",
        }
    )

    return {
        "access_token": token,
        "token_type": "bearer",
    }
