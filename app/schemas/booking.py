from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class BookingCreate(BaseModel):
    business_id: int
    enquiry_id: Optional[int] = None
    start_time: datetime
    end_time: datetime


class BookingOut(BaseModel):
    id: int
    business_id: int
    enquiry_id: Optional[int]
    start_time: datetime
    end_time: datetime
    created_at: datetime

    model_config = {"from_attributes": True}
