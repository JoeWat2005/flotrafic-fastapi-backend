from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


# ----------------------------
# Used by PUBLIC booking form
# ----------------------------
class PublicBookingCreate(BaseModel):
    start_time: datetime
    end_time: datetime
    customer_email: EmailStr


# ----------------------------
# Used by BUSINESS dashboard
# ----------------------------
class BookingFromEnquiryCreate(BaseModel):
    start_time: datetime
    end_time: datetime

# ----------------------------
# Used when returning bookings
# ----------------------------
class BookingOut(BaseModel):
    id: int
    business_id: int
    enquiry_id: Optional[int]
    start_time: datetime
    end_time: datetime
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

