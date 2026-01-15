from pydantic import BaseModel, Field, EmailStr
from typing import Optional

"""
ME ROUTE SCHEMA
"""


#Authenticated business profile returned by the /me endpoint
class MeOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    tier: str
    is_active: bool
    slug: str

    model_config = {"from_attributes": True}


#Billing and subscription information returned for the current business
class BillingOut(BaseModel):
    tier: str
    is_active: bool
    subscription_status: Optional[str] = None
    current_period_end: Optional[int] = None
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None


#Payload used to update the business display name
class UpdateMe(BaseModel):
    name: str = Field(min_length=1, max_length=100)


#Payload used when changing the account password
class ChangePassword(BaseModel):
    old_password: str
    new_password: str