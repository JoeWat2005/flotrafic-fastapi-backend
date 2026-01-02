from pydantic import BaseModel, EmailStr
from typing import Literal


class BusinessCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    tier: Literal["foundation", "managed", "autopilot"]


class BusinessOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    tier: str

    model_config = {"from_attributes": True}

