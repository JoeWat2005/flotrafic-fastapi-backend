from sqlalchemy.orm import Session
from app.db.models import AuditLog


def log_action(
    db: Session,
    actor_type: str,
    actor_id: int,
    action: str,
    details: str | None = None,
):
    log = AuditLog(
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        details=details,
    )
    db.add(log)
    db.commit()
