from pydantic import BaseModel
from datetime import datetime
from typing import Optional

"""
BOOKINGS ROUTE SCHEMA
"""


#Payload used when creating a booking from an existing enquiry
class BookingFromEnquiryCreate(BaseModel):
    start_time: datetime
    end_time: datetime


#Response model representing a booking returned to the dashboard
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


#Payload used to update internal notes attached to a booking
class BookingNotesUpdate(BaseModel):
    notes: str
