from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, Query
from typing import List, Optional
from datetime import datetime, timezone

from app.db.session import get_db
from app.db.models import Booking, Enquiry, Business
from app.schemas.booking import BookingFromEnquiryCreate, BookingOut
from app.api.deps import require_feature
from app.services.email import (
    send_booking_confirmed_customer,
    send_booking_cancelled_customer,
)

router = APIRouter(
    prefix="/bookings",
    tags=["Bookings"],
    dependencies=[Depends(require_feature("bookings"))],
)


@router.get("/", response_model=List[BookingOut])
def get_bookings(
    status: Optional[str] = Query(
        None,
        pattern="^(pending|confirmed|cancelled)$"
    ),
    sort: str = Query(
        "upcoming",
        pattern="^(upcoming|past|created)$"
    ),
    limit: int = Query(20, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_business: Business = Depends(require_feature("bookings")),
):
    now = datetime.now(timezone.utc)

    query = (
        db.query(Booking)
        .filter(Booking.business_id == current_business.id)
    )

    if status:
        query = query.filter(Booking.status == status)

    # 🔽 SORTING
    if sort == "past":
        query = (
            query
            .filter(Booking.end_time < now)
            .order_by(Booking.start_time.desc())
        )
    elif sort == "created":
        query = query.order_by(Booking.created_at.desc())
    else:  # upcoming
        query = (
            query
            .filter(Booking.end_time >= now)
            .order_by(Booking.start_time.asc())
        )

    return query.offset(offset).limit(limit).all()


@router.post("/{booking_id}/confirm")
def confirm_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_business: Business = Depends(require_feature("bookings")),
):
    booking = (
        db.query(Booking)
        .filter(
            Booking.id == booking_id,
            Booking.business_id == current_business.id,
            Booking.status == "pending",
        )
        .first()
    )

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found or already confirmed")

    booking.status = "confirmed"
    db.commit()
    db.refresh(booking)

    if booking.enquiry_id:
        enquiry = db.query(Enquiry).filter(Enquiry.id == booking.enquiry_id).first()
        if enquiry:
            send_booking_confirmed_customer(
                customer_email=enquiry.email,
                business_name=current_business.name,
                business_email=current_business.email,
                start_time=booking.start_time,
            )

    return {"success": True}


@router.delete("/{booking_id}")
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_business: Business = Depends(require_feature("bookings")),
):
    booking = (
        db.query(Booking)
        .filter(
            Booking.id == booking_id,
            Booking.business_id == current_business.id,
        )
        .first()
    )

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    booking.status = "cancelled"
    db.commit()

    if booking.enquiry_id:
        enquiry = db.query(Enquiry).filter(Enquiry.id == booking.enquiry_id).first()
        if enquiry:
            send_booking_cancelled_customer(
                customer_email=enquiry.email,
                business_name=current_business.name,
                start_time=booking.start_time,
            )

    return {"success": True}

@router.post("/from-enquiry/{enquiry_id}")
def create_booking_from_enquiry(
    enquiry_id: int,
    payload: BookingFromEnquiryCreate,
    db: Session = Depends(get_db),
    current_business: Business = Depends(require_feature("bookings")),
):
    # 1. Fetch enquiry (must belong to this business)
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

    # 2. Prevent duplicate bookings for one enquiry
    existing = (
        db.query(Booking)
        .filter(Booking.enquiry_id == enquiry.id)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="This enquiry already has a booking",
        )

    # 3. Create CONFIRMED booking (business-picked time)
    booking = Booking(
        business_id=current_business.id,
        enquiry_id=enquiry.id,
        start_time=payload.start_time,
        end_time=payload.end_time,
        status="confirmed",
    )

    db.add(booking)

    # 4. Update enquiry status
    enquiry.status = "in_progress"

    db.commit()
    db.refresh(booking)

    # 5. Notify customer (confirmed booking)
    send_booking_confirmed_customer(
        customer_email=enquiry.email,
        business_name=current_business.name,
        business_email=current_business.email,
        start_time=booking.start_time,
    )

    return {
        "success": True,
        "booking_id": booking.id,
    }




