from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Literal

from app.core.config import PASSWORD_REGEX

"""
AUTH ROUTE SCHEMA
"""


#Response returned after successful authentication containing the JWT
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


#Payload used during initial pre-registration before email verification
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


#Payload used by businesses to log in with email and password
class LoginRequest(BaseModel):
    username: EmailStr
    password: str


#Payload used to verify an email address using a one-time code
class VerifyEmailCodeRequest(BaseModel):
    email: EmailStr
    code: str
    captcha_token: str


#Payload used to reset a password after email verification
class PasswordResetConfirmRequest(BaseModel):
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
    
class PasswordResetRequest(BaseModel):
    email: EmailStr
