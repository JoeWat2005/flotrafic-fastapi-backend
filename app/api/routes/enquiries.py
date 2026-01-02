from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.db.models import Enquiry, Business
from app.schemas.enquiry import EnquiryCreate, EnquiryOut

router = APIRouter(prefix="/enquiries", tags=["Enquiries"])


@router.post("/", response_model=dict)
def create_enquiry(
    payload: EnquiryCreate,
    business_id: int,
    db: Session = Depends(get_db),
):
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    enquiry = Enquiry(
        name=payload.name,
        email=payload.email,
        message=payload.message,
        business_id=business_id,
    )

    db.add(enquiry)
    db.commit()

    return {"success": True}


@router.get("/", response_model=List[EnquiryOut])
def get_enquiries(
    business_id: int,
    is_read: Optional[bool] = None,
    status: Optional[str] = None,
    limit: int = Query(20, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(Enquiry).filter(Enquiry.business_id == business_id)

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
    business_id: int,
    db: Session = Depends(get_db),
):
    enquiry = (
        db.query(Enquiry)
        .filter(
            Enquiry.id == enquiry_id,
            Enquiry.business_id == business_id,
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
    business_id: int,
    status: str = Query(..., regex="^(new|in_progress|resolved)$"),
    db: Session = Depends(get_db),
):
    enquiry = (
        db.query(Enquiry)
        .filter(
            Enquiry.id == enquiry_id,
            Enquiry.business_id == business_id,
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
    business_id: int,
    db: Session = Depends(get_db),
):
    enquiry = (
        db.query(Enquiry)
        .filter(
            Enquiry.id == enquiry_id,
            Enquiry.business_id == business_id,
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
