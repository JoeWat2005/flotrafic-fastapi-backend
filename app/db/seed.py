from sqlalchemy.orm import Session

from app.db.models import Business
from app.core.security import hash_password


def seed_business(db: Session):
    existing = db.query(Business).first()
    if existing:
        return

    lowtier = Business(
        name="lowtier",
        tier="foundation",
        hashed_password=hash_password("password"),
    )

    midtier = Business(
        name="midtier",
        tier="managed",
        hashed_password=hash_password("password"),
    )

    db.add_all([lowtier, midtier])
    db.commit()


