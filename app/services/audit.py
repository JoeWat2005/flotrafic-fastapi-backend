from sqlalchemy.orm import Session
from app.db.models import AuditLog


def log_action(
    db: Session,
    actor_type: str,
    actor_id: int,
    action: str,
    details: str | None = None,
):
    try:
        log = AuditLog(
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            details=details,
        )
        db.add(log)
        db.flush()
    except Exception:
        # Don't let audit logging break the real request
        db.rollback()
