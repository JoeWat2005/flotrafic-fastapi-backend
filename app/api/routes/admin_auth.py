from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Admin
from app.core.security import verify_password
from app.core.jwt import create_access_token
from app.services.audit import log_action
from app.core.rate_limit import rate_limit
from app.schemas.admin_auth import AdminLogin

router = APIRouter(prefix="/admin/auth", tags=["Admin Auth"])

"""
ADMIN AUTH ROUTES => NO FEATURE GATING OR BUSINESS AUTH

INSTEAD:

1) ADMIN/AUTH/LOGIN => RATE LIMIT OF 5 ATTEMPTS / 10 MINUTES / IP
"""

#admin login
@router.post("/login")
def admin_login(
    payload: AdminLogin,
    request: Request,
    db: Session = Depends(get_db),
):
    # Rate limit: 5 attempts / 10 minutes / IP
    ip = request.client.host if request.client else "unknown"
    key = f"admin_login:{ip}"

    if not rate_limit(key, max_requests=5, window_seconds=600):
        raise HTTPException(status_code=429, detail="Too many login attempts")

    username = payload.username.strip()
    password = payload.password

    admin = (
        db.query(Admin)
        .filter(Admin.username == username)
        .first()
    )

    if not admin or not verify_password(password, admin.hashed_password):
        log_action(
            db=db,
            actor_type="admin",
            actor_id=0,
            action="admin.login_failed",
            details=f"username={username}",
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

