from sqlalchemy.orm import Session

from app.db.models import Admin
from app.core.security import hash_password

def seed_admin(db: Session):
    existing = db.query(Admin).first()
    if existing:
        return

    admin = Admin(
        username="admin",
        hashed_password=hash_password("password"),
    )

    db.add(admin)
    db.commit()




