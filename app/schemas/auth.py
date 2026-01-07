from pydantic import BaseModel, EmailStr, Field
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
    captcha_token: str

    @classmethod
    def validate_password(cls, password: str):
        if not PASSWORD_REGEX.match(password):
            raise ValueError(
                "Password must be at least 8 characters long and include "
                "a number and a symbol"
            )

    @classmethod
    def validate_confirm(cls, password: str, confirm: str):
        if password != confirm:
            raise ValueError("Passwords do not match")
