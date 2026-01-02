from fastapi import APIRouter, Depends, Request, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from typing import List, Optional

from app.db.session import get_db
from app.db.models import ContactMessage
from app.schemas.contact import ContactCreate, ContactOut
from app.services.email import send_email
from app.api.deps import get_current_admin

router = APIRouter(
    prefix="/contact",
    tags=["Contact"],
)

# =========================
# 🔓 PUBLIC: submit contact
# =========================
@router.post("/", response_model=dict)
def submit_contact(
    payload: ContactCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    ip = request.client.host
    ua = request.headers.get("user-agent")

    one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
    recent = (
        db.query(ContactMessage)
        .filter(
            ContactMessage.ip_address == ip,
            ContactMessage.created_at >= one_minute_ago,
        )
        .first()
    )
    if recent:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait a moment.",
        )

    msg = ContactMessage(
        name=payload.name,
        email=payload.email,
        message=payload.message,
        ip_address=ip,
        user_agent=ua,
    )
    db.add(msg)
    db.commit()

    send_email(
        to="you@flotrafic.co.uk",
        subject="New Flotrafic contact message",
        body=f"""
New contact submission

Name: {payload.name}
Email: {payload.email}

Message:
{payload.message}
""",
    )

    return {"success": True}


# =========================
# 🔒 ADMIN: list contacts
# =========================
@router.get("/", response_model=List[ContactOut])
def list_contacts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin),
):
    query = db.query(ContactMessage)

    if search:
        like = f"%{search}%"
        query = query.filter(
            (ContactMessage.name.ilike(like)) |
            (ContactMessage.email.ilike(like)) |
            (ContactMessage.message.ilike(like))
        )

    return (
        query
        .order_by(ContactMessage.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )


# =========================
# 🔒 ADMIN: delete contact
# =========================
@router.delete("/{contact_id}", response_model=dict)
def delete_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin),
):
    contact = (
        db.query(ContactMessage)
        .filter(ContactMessage.id == contact_id)
        .first()
    )

    if not contact:
        raise HTTPException(
            status_code=404,
            detail="Contact message not found",
        )

    db.delete(contact)
    db.commit()

    return {"success": True}
