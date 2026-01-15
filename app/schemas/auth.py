from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Literal

from app.core.config import PASSWORD_REGEX

"""
AUTH ROUTE SCHEMA
"""

#token
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

#pre register
class PreRegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str
    confirm_password: str
    tier: Literal["free", "pro"]

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

#login
class LoginRequest(BaseModel):
    username: EmailStr
    password: str

#verify
class VerifyEmailCodeRequest(BaseModel):
    email: EmailStr
    code: str
    captcha_token: str

#reset password
class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str
    captcha_token: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str):
        if not PASSWORD_REGEX.match(v):
            raise ValueError(
                "Password must be at least 8 characters long and include "
                "a number and a symbol"
            )
        return v

