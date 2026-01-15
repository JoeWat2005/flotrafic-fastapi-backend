from sqlalchemy.orm import Session
from app.db.models import AuditLog


#Persist a single audit log entry without interrupting the main request flow
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
        #Never allow audit logging failures to break application logic
        db.rollback()