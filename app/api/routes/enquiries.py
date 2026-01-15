from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Literal

from app.db.session import get_db
from app.db.models import Enquiry, Business, Visit
from app.schemas.enquirys import EnquiryOut, EnquiryStatusUpdate
from app.api.deps import get_current_business, require_feature
from app.services.audit import log_action

router = APIRouter(
    prefix="/enquiries",
    tags=["Enquiries"],
    dependencies=[Depends(require_feature("enquiries"))],
)


"""
ENQUIRY ROUTES => CUSTOMER MESSAGES & LEADS

Handles incoming customer enquiries,
status updates, and enquiry analytics.
"""

#Retrieve enquiries with filtering, sorting, and pagination
@router.get("/", response_model=List[EnquiryOut])
def get_enquiries(
    is_read: Optional[bool] = Query(None),
    status: Optional[Literal["new", "in_progress", "resolved"]] = Query(None),
    sort: Literal["newest", "oldest", "unread", "status"] = Query("newest"),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    query = db.query(Enquiry).filter(Enquiry.business_id == business.id)

    if is_read is not None:
        query = query.filter(Enquiry.is_read == is_read)

    if status is not None:
        query = query.filter(Enquiry.status == status)

    if sort == "oldest":
        query = query.order_by(Enquiry.created_at.asc())
    elif sort == "unread":
        query = query.order_by(
            Enquiry.is_read.asc(),
            Enquiry.created_at.desc(),
        )
    elif sort == "status":
        query = query.order_by(
            Enquiry.status.asc(),
            Enquiry.created_at.desc(),
        )
    else:
        query = query.order_by(Enquiry.created_at.desc())

    return query.offset(offset).limit(limit).all()


#Mark an enquiry as read without modifying its status
@router.patch("/{enquiry_id}/read")
def mark_enquiry_read(
    enquiry_id: int,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    enquiry = (
        db.query(Enquiry)
        .filter(
            Enquiry.id == enquiry_id,
            Enquiry.business_id == business.id,
        )
        .first()
    )

    if not enquiry:
        raise HTTPException(404, "Enquiry not found")

    enquiry.is_read = True
    db.commit()

    log_action(
        db=db,
        actor_type="business",
        actor_id=business.id,
        action="enquiry.marked_read",
        details=f"enquiry_id={enquiry.id}",
    )

    return {"success": True}


#Update the workflow status of an enquiry
@router.patch("/{enquiry_id}/status")
def update_enquiry_status(
    enquiry_id: int,
    payload: EnquiryStatusUpdate,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    enquiry = (
        db.query(Enquiry)
        .filter(
            Enquiry.id == enquiry_id,
            Enquiry.business_id == business.id,
        )
        .first()
    )

    if not enquiry:
        raise HTTPException(404, "Enquiry not found")

    enquiry.status = payload.status
    db.commit()

    log_action(
        db=db,
        actor_type="business",
        actor_id=business.id,
        action="enquiry.status_changed",
        details=f"enquiry_id={enquiry.id},status={payload.status}",
    )

    return {"success": True}


#Delete an enquiry if it has no associated booking
@router.delete("/{enquiry_id}")
def delete_enquiry(
    enquiry_id: int,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    enquiry = (
        db.query(Enquiry)
        .filter(
            Enquiry.id == enquiry_id,
            Enquiry.business_id == business.id,
        )
        .first()
    )

    if not enquiry:
        raise HTTPException(404, "Enquiry not found")

    if enquiry.bookings:
        raise HTTPException(
            400,
            "Cannot delete enquiry with existing booking",
        )

    db.delete(enquiry)
    db.commit()

    log_action(
        db=db,
        actor_type="business",
        actor_id=business.id,
        action="enquiry.deleted",
        details=f"enquiry_id={enquiry_id}",
    )

    return {"success": True}


#Return enquiry and visit statistics for dashboard insights
@router.get("/stats")
def enquiry_stats(
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    return {
        "total": db.query(Enquiry)
        .filter(Enquiry.business_id == business.id)
        .count(),

        "unread": db.query(Enquiry)
        .filter(
            Enquiry.business_id == business.id,
            Enquiry.is_read.is_(False),
        )
        .count(),

        "new": db.query(Enquiry)
        .filter(
            Enquiry.business_id == business.id,
            Enquiry.status == "new",
        )
        .count(),

        "visits": db.query(Visit)
        .filter(Visit.business_id == business.id)
        .count(),
    }