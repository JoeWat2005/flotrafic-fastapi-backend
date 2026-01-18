from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Literal
from datetime import datetime, timezone

from app.db.session import get_db
from app.db.models import Booking, Enquiry, Business
from app.schemas.bookings import BookingFromEnquiryCreate, BookingOut, BookingNotesUpdate
from app.api.deps import get_current_business, require_feature
from app.services.email import (
    send_booking_confirmed_customer,
    send_booking_cancelled_customer,
)
from app.services.audit import log_action

router = APIRouter(
    prefix="/bookings",
    tags=["Bookings"],
    dependencies=[Depends(require_feature("bookings"))],
)


"""
BOOKING ROUTES => APPOINTMENTS & SCHEDULING

Manages bookings created manually, from enquiries,
or via public booking requests.
"""


#Retrieve bookings with optional status filtering and sorting
@router.get("/", response_model=List[BookingOut])
def get_bookings(
    status: Optional[Literal["pending", "confirmed", "cancelled"]] = Query(None),
    sort: Literal["upcoming", "past", "created"] = Query("upcoming"),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    now = datetime.now(timezone.utc)

    query = db.query(Booking).filter(
        Booking.business_id == business.id,
        Booking.status != "cancelled",
        )

    if status:
        query = query.filter(Booking.status == status)

    if sort == "past":
        query = query.filter(Booking.end_time < now).order_by(Booking.start_time.desc())
    elif sort == "created":
        query = query.order_by(Booking.created_at.desc())
    else:
        query = query.filter(Booking.end_time >= now).order_by(Booking.start_time.asc())

    return query.offset(offset).limit(limit).all()


#Confirm a pending booking and notify the customer
@router.post("/{booking_id}/confirm")
def confirm_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    booking = (
        db.query(Booking)
        .filter(
            Booking.id == booking_id,
            Booking.business_id == business.id,
            Booking.status == "pending",
        )
        .first()
    )

    if not booking:
        raise HTTPException(404, "Booking not found or already confirmed")

    booking.status = "confirmed"
    db.commit()
    db.refresh(booking)

    log_action(
        db=db,
        actor_type="business",
        actor_id=business.id,
        action="booking.confirmed",
        details=f"booking_id={booking.id}",
    )

    if booking.enquiry_id:
        enquiry = db.query(Enquiry).get(booking.enquiry_id)
        if enquiry:
            send_booking_confirmed_customer(
                customer_email=enquiry.email,
                business_name=business.name,
                business_email=business.email,
                start_time=booking.start_time,
            )

    return {"success": True}


#Cancel an existing booking and notify the customer if applicable
@router.delete("/{booking_id}")
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    booking = (
        db.query(Booking)
        .filter(
            Booking.id == booking_id,
            Booking.business_id == business.id,
        )
        .first()
    )

    if not booking:
        raise HTTPException(404, "Booking not found")

    booking.status = "cancelled"
    db.commit()

    log_action(
        db=db,
        actor_type="business",
        actor_id=business.id,
        action="booking.cancelled",
        details=f"booking_id={booking.id}",
    )

    if booking.enquiry_id:
        enquiry = db.query(Enquiry).get(booking.enquiry_id)
        if enquiry:
            send_booking_cancelled_customer(
                customer_email=enquiry.email,
                business_name=business.name,
                start_time=booking.start_time,
            )

    return {"success": True}


#Create and immediately confirm a booking from an enquiry
@router.post("/from-enquiry/{enquiry_id}")
def create_booking_from_enquiry(
    enquiry_id: int,
    payload: BookingFromEnquiryCreate,
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

    existing = db.query(Booking).filter(
        Booking.enquiry_id == enquiry.id,
        Booking.status != "cancelled"
        ).first()
    if existing:
        raise HTTPException(400, "This enquiry already has a booking")
    
    if payload.end_time <= payload.start_time:
        raise HTTPException(
            400,
            "End time must be after start time",
        )

    booking = Booking(
        business_id=business.id,
        enquiry_id=enquiry.id,
        start_time=payload.start_time,
        end_time=payload.end_time,
        status="confirmed",
    )

    db.add(booking)
    enquiry.status = "in_progress"
    db.commit()
    db.refresh(booking)

    log_action(
        db=db,
        actor_type="business",
        actor_id=business.id,
        action="booking.created_from_enquiry",
        details=f"booking_id={booking.id},enquiry_id={enquiry.id}",
    )

    send_booking_confirmed_customer(
        customer_email=enquiry.email,
        business_name=business.name,
        business_email=business.email,
        start_time=booking.start_time,
    )

    return {"success": True, "booking_id": booking.id}


#Update internal notes attached to a booking
@router.patch("/{booking_id}/notes")
def update_booking_notes(
    booking_id: int,
    payload: BookingNotesUpdate,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    booking = (
        db.query(Booking)
        .filter(
            Booking.id == booking_id,
            Booking.business_id == business.id,
        )
        .first()
    )

    if not booking:
        raise HTTPException(404, "Booking not found")

    booking.notes = payload.notes
    db.commit()

    return {"success": True}