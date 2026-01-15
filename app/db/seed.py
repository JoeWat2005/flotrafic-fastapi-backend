from sqlalchemy.orm import Session

from app.db.models import Admin
from app.core.config import settings

#seed database admin
def seed_admin(db: Session):
    existing = db.query(Admin).first()
    if existing:
        return

    admin = Admin(
        username="admin",
        hashed_password=settings.ADMIN_PASSWORD,
    )

    db.add(admin)
    db.commit()