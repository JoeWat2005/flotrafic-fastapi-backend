from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.db.models import Booking, Business, Enquiry
from app.schemas.booking import BookingCreate, BookingOut

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("/", response_model=dict)
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
):
    # 1️⃣ Validate business exists
    business = db.query(Business).filter(Business.id == payload.business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    # 2️⃣ Validate time range
    if payload.end_time <= payload.start_time:
        raise HTTPException(
            status_code=400,
            detail="end_time must be after start_time",
        )

    # 3️⃣ Prevent overlapping bookings
    conflict = (
        db.query(Booking)
        .filter(
            Booking.business_id == payload.business_id,
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
                Enquiry.business_id == payload.business_id,
            )
            .first()
        )
        if not enquiry:
            raise HTTPException(status_code=404, detail="Enquiry not found")

    booking = Booking(
        business_id=payload.business_id,
        enquiry_id=payload.enquiry_id,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )

    db.add(booking)

    # 4️⃣ Auto-update enquiry status
    if enquiry:
        enquiry.status = "in_progress"

    db.commit()

    return {"success": True}


@router.get("/", response_model=List[BookingOut])
def get_bookings(
    business_id: int,
    db: Session = Depends(get_db),
):
    return (
        db.query(Booking)
        .filter(Booking.business_id == business_id)
        .order_by(Booking.start_time)
        .all()
    )


@router.delete("/{booking_id}", response_model=dict)
def delete_booking(
    booking_id: int,
    business_id: int,
    db: Session = Depends(get_db),
):
    booking = (
        db.query(Booking)
        .filter(
            Booking.id == booking_id,
            Booking.business_id == business_id,
        )
        .first()
    )

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    db.delete(booking)
    db.commit()

    return {"success": True}
