from sqlalchemy.orm import Session
from app.db.models import Business


def seed_business(db: Session):
    existing = db.query(Business).first()
    if existing:
        return

    business = Business(
        name="Flotrafic Default",
        tier="foundation",
    )
    db.add(business)
    db.commit()
