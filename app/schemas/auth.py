from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Literal
import re

PASSWORD_REGEX = re.compile(
    r"^(?=.*[0-9])(?=.*[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]).{8,}$"
)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PreRegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str
    confirm_password: str
    tier: Literal["foundation", "managed", "autopilot"]

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str):
        if not PASSWORD_REGEX.match(v):
            raise ValueError(
                "Password must be at least 8 characters long and include "
                "a number and a symbol"
            )
        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, info):
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v
