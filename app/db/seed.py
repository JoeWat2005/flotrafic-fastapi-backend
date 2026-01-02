from sqlalchemy.orm import Session

from app.db.models import Business, Admin
from app.core.security import hash_password


def seed_business(db: Session):
    existing = db.query(Business).first()
    if existing:
        return

    lowtier = Business(
        name="lowtier",
        email="lowtier@test.com",
        tier="foundation",
        hashed_password=hash_password("password"),
        is_active=True,
    )

    midtier = Business(
        name="midtier",
        email="midtier@test.com",
        tier="managed",
        hashed_password=hash_password("password"),
        is_active=True,
    )

    db.add_all([lowtier, midtier])
    db.commit()


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




