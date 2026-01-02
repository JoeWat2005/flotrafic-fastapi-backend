from sqlalchemy.orm import Session

from app.db.models import Business
from app.core.security import hash_password


def seed_business(db: Session):
    existing = db.query(Business).first()
    if existing:
        return

    business = Business(
        name="Flotrafic Default",
        tier="foundation",
        hashed_password=hash_password("password123"),
    )

    db.add(business)
    db.commit()
