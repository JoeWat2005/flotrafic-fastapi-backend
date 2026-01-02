from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.db.models import Booking, Enquiry, Business
from app.schemas.booking import BookingCreate, BookingOut
from app.api.deps import get_current_business

router = APIRouter(
    prefix="/bookings",
    tags=["Bookings"],
)


@router.post("/", response_model=dict)
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business),
):
    # 1️⃣ Validate time range
    if payload.end_time <= payload.start_time:
        raise HTTPException(
            status_code=400,
            detail="end_time must be after start_time",
        )

    # 2️⃣ Prevent overlapping bookings for this business
    conflict = (
        db.query(Booking)
        .filter(
            Booking.business_id == current_business.id,
            Booking.start_time < payload.end_time,
            Booking.end_time > payload.start_time,
        )
        .first()
    )

    if conflict:
        raise HTTPException(
            status_code=400,
            detail="Booking overlaps with an existing booking",
        )

    enquiry = None
    if payload.enquiry_id:
        enquiry = (
            db.query(Enquiry)
            .filter(
                Enquiry.id == payload.enquiry_id,
                Enquiry.business_id == current_business.id,
            )
            .first()
        )

        if not enquiry:
            raise HTTPException(status_code=404, detail="Enquiry not found")

    booking = Booking(
        business_id=current_business.id,
        enquiry_id=payload.enquiry_id,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )

    db.add(booking)

    # 3️⃣ Auto-update enquiry status
    if enquiry:
        enquiry.status = "in_progress"

    db.commit()

    return {"success": True}


@router.get("/", response_model=List[BookingOut])
def get_bookings(
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business),
):
    return (
        db.query(Booking)
        .filter(Booking.business_id == current_business.id)
        .order_by(Booking.start_time)
        .all()
    )


@router.delete("/{booking_id}", response_model=dict)
def delete_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business),
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

    db.delete(booking)
    db.commit()

    return {"success": True}

