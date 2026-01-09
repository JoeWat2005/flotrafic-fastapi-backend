from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Admin
from app.core.security import verify_password
from app.core.jwt import create_access_token
from app.services.audit import log_action

router = APIRouter(prefix="/admin/auth", tags=["Admin Auth"])


@router.post("/login")
def admin_login(payload: dict, db: Session = Depends(get_db)):
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""

    admin = (
        db.query(Admin)
        .filter(Admin.username == username)
        .first()
    )

    if not admin or not verify_password(password, admin.hashed_password):
        # Keep external error minimal; log details internally
        log_action(
            db=db,
            actor_type="admin",
            actor_id=0,
            action="admin.login_failed",
            details=f"username={username}",
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(
        {
            "sub": str(admin.id),
            "type": "admin",
        }
    )

    return {"access_token": token, "token_type": "bearer"}
