from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.db.models import Enquiry, Business
from app.schemas.enquiry import EnquiryCreate, EnquiryOut
from app.api.deps import get_current_business
from app.services.email import send_email

router = APIRouter(
    prefix="/enquiries",
    tags=["Enquiries"],
)


@router.post("/", response_model=dict)
def create_enquiry(
    payload: EnquiryCreate,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business),
):
    enquiry = Enquiry(
        name=payload.name,
        email=payload.email,
        message=payload.message,
        business_id=current_business.id,
    )

    db.add(enquiry)
    db.commit()

    # 📧 Email BUSINESS only
    send_email(
        to=current_business.name,  # replace with business.email later
        subject="New enquiry received",
        body=(
            f"New enquiry received\n\n"
            f"Name: {payload.name}\n"
            f"Email: {payload.email}\n\n"
            f"Message:\n{payload.message}"
        ),
    )

    return {"success": True}


@router.get("/", response_model=List[EnquiryOut])
def get_enquiries(
    is_read: Optional[bool] = None,
    status: Optional[str] = None,
    limit: int = Query(20, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business),
):
    query = (
        db.query(Enquiry)
        .filter(Enquiry.business_id == current_business.id)
    )

    if is_read is not None:
        query = query.filter(Enquiry.is_read == is_read)

    if status:
        query = query.filter(Enquiry.status == status)

    return (
        query
        .order_by(Enquiry.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.patch("/{enquiry_id}/read", response_model=dict)
def mark_enquiry_read(
    enquiry_id: int,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business),
):
    enquiry = (
        db.query(Enquiry)
        .filter(
            Enquiry.id == enquiry_id,
            Enquiry.business_id == current_business.id,
        )
        .first()
    )

    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")

    enquiry.is_read = True
    db.commit()

    return {"success": True}


@router.patch("/{enquiry_id}/status", response_model=dict)
def update_enquiry_status(
    enquiry_id: int,
    status: str = Query(..., regex="^(new|in_progress|resolved)$"),
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business),
):
    enquiry = (
        db.query(Enquiry)
        .filter(
            Enquiry.id == enquiry_id,
            Enquiry.business_id == current_business.id,
        )
        .first()
    )

    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")

    enquiry.status = status
    db.commit()

    return {"success": True}


@router.delete("/{enquiry_id}", response_model=dict)
def delete_enquiry(
    enquiry_id: int,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business),
):
    enquiry = (
        db.query(Enquiry)
        .filter(
            Enquiry.id == enquiry_id,
            Enquiry.business_id == current_business.id,
        )
        .first()
    )

    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")

    if enquiry.bookings:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete enquiry with existing booking",
        )

    db.delete(enquiry)
    db.commit()

    return {"success": True}
