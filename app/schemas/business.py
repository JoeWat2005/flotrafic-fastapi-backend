from pydantic import BaseModel, EmailStr
from typing import Literal

"""
BUSINESS ROUTE SCHEMA
"""


#Public-facing representation of a business for admin dashboards
class BusinessOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    tier: str
    is_active: bool

    model_config = {"from_attributes": True}


#Payload used by admins to change a business subscription tier
class BusinessTierUpdate(BaseModel):
    tier: Literal["free", "pro"]

