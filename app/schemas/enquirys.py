from pydantic import BaseModel, EmailStr
from typing import Literal
from datetime import datetime

"""
ENQUIRIES ROUTE SCHEMA
"""


EnquiryStatus = Literal["new", "in_progress", "resolved"]


#Payload used when a customer submits a new enquiry
class EnquiryCreate(BaseModel):
    name: str
    email: EmailStr
    message: str


#Payload used to update the status of an existing enquiry
class EnquiryStatusUpdate(BaseModel):
    status: EnquiryStatus


#Response model representing an enquiry in the dashboard
class EnquiryOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    message: str
    created_at: datetime
    is_read: bool
    status: EnquiryStatus

    model_config = {"from_attributes": True}