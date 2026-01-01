from pydantic import BaseModel
from typing import Literal


class BusinessCreate(BaseModel):
    name: str
    tier: Literal["foundation", "managed", "autopilot"]


class BusinessOut(BaseModel):
    id: int
    name: str
    tier: str

    model_config = {"from_attributes": True}
