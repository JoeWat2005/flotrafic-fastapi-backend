from pydantic import BaseModel, EmailStr
from typing import Literal

class BusinessOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    tier: str
    is_active: bool

    model_config = {"from_attributes": True}


class BusinessTierUpdate(BaseModel):
    tier: Literal["free", "pro"]

