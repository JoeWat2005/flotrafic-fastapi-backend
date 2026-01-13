from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Literal

from app.db.session import get_db
from app.db.models import Enquiry, Business, Visit
from app.schemas.enquiry import EnquiryOut
from app.api.deps import get_current_business, require_feature
from app.services.audit import log_action


# 🔒 Enquiries: create = ALL TIERS, manage = enquiries_manage
router = APIRouter(
    prefix="/enquiries",
    tags=["Enquiries"],
    dependencies=[Depends(get_current_business)],
)


@router.get("/", response_model=List[EnquiryOut])
def get_enquiries(
    is_read: Optional[bool] = Query(None),
    status: Optional[Literal["new", "in_progress", "resolved"]] = Query(None),
    sort: Literal["newest", "oldest", "unread", "status"] = Query("newest"),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_business: Business = Depends(require_feature("enquiries_manage")),
):
    query = (
        db.query(Enquiry)
        .filter(Enquiry.business_id == current_business.id)
    )

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
    else:  # newest
        query = query.order_by(Enquiry.created_at.desc())

    return query.offset(offset).limit(limit).all()



@router.patch("/{enquiry_id}/read", response_model=dict)
def mark_enquiry_read(
    enquiry_id: int,
    db: Session = Depends(get_db),
    current_business: Business = Depends(require_feature("enquiries_manage")),
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

    log_action(
        db=db,
        actor_type="business",
        actor_id=current_business.id,
        action="enquiry.marked_read",
        details=f"enquiry_id={enquiry.id}",
    )

    return {"success": True}


@router.patch("/{enquiry_id}/status", response_model=dict)
def update_enquiry_status(
    enquiry_id: int,
    status: str = Query(..., pattern="^(new|in_progress|resolved)$"),
    db: Session = Depends(get_db),
    current_business: Business = Depends(require_feature("enquiries_manage")),
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

    log_action(
        db=db,
        actor_type="business",
        actor_id=current_business.id,
        action="enquiry.status_changed",
        details=f"enquiry_id={enquiry.id},status={status}",
    )

    return {"success": True}


@router.delete("/{enquiry_id}", response_model=dict)
def delete_enquiry(
    enquiry_id: int,
    db: Session = Depends(get_db),
    current_business: Business = Depends(require_feature("enquiries_manage")),
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

    log_action(
        db=db,
        actor_type="business",
        actor_id=current_business.id,
        action="enquiry.deleted",
        details=f"enquiry_id={enquiry_id}",
    )

    return {"success": True}

@router.get("/stats")
def enquiry_stats(
    db: Session = Depends(get_db),
    business: Business = Depends(require_feature("enquiries_manage")),
):
    return {
        "total": db.query(Enquiry)
            .filter(Enquiry.business_id == business.id)
            .count(),

        "unread": db.query(Enquiry)
            .filter(
                Enquiry.business_id == business.id,
                Enquiry.is_read == False,
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
            .count()
    }


@router.patch("/bulk-read")
def mark_all_read(
    db: Session = Depends(get_db),
    business: Business = Depends(require_feature("enquiries_manage")),
):
    (
        db.query(Enquiry)
        .filter(
            Enquiry.business_id == business.id,
            Enquiry.is_read == False,
        )
        .update({Enquiry.is_read: True})
    )
    db.commit()

    return {"success": True}
