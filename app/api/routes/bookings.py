from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.db.session import get_db
from app.db.models import Booking, Enquiry, Business
from app.schemas.booking import BookingCreate, BookingOut
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
    db: Session = Depends(get_db),
    current_business: Business = Depends(require_feature("bookings")),
):
    return (
        db.query(Booking)
        .filter(Booking.business_id == current_business.id)
        .order_by(Booking.start_time)
        .all()
    )


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





