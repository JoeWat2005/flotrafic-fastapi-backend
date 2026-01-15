from pydantic import BaseModel
from datetime import datetime
from typing import Optional

#booking from enquiry
class BookingFromEnquiryCreate(BaseModel):
    start_time: datetime
    end_time: datetime

#booking out
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

#note update
class BookingNotesUpdate(BaseModel):
    notes: str
