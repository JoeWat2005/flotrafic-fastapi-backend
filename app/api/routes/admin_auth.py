from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Admin
from app.core.security import verify_password
from app.core.jwt import create_access_token

router = APIRouter(prefix="/admin/auth", tags=["Admin Auth"])


@router.post("/login")
def admin_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    admin = (
        db.query(Admin)
        .filter(Admin.username == form_data.username)
        .first()
    )

    if not admin or not verify_password(
        form_data.password,
        admin.hashed_password,
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")

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
