from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.db.models import Booking
from app.schemas.booking import BookingCreate, BookingOut

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("/", response_model=dict)
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
):
    booking = Booking(**payload.model_dump())
    db.add(booking)
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
