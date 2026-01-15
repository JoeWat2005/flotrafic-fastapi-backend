from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
import requests
from fastapi import HTTPException
from time import time

from app.core.config import settings

"""
API SECURITY
"""

SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
_RATE_LIMIT_STORE = {}

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
)


#Hash plaintext password
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


#Check whether plaintext password matches a stored hash
def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)


#Create JWT access token
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


#Verify cloudflare turnstile CAPTCHA token
def verify_captcha(token: str):
    res = requests.post(
        "https://challenges.cloudflare.com/turnstile/v0/siteverify",
        json={
            "secret": settings.TURNSTILE_SECRET_KEY,
            "response": token,
        },
        timeout=5,
    )

    data = res.json()

    if not data.get("success"):
        raise HTTPException(
            status_code=400,
            detail=f"Captcha verification failed: {data}",
        )


#Simple in-memory rate limiter
def rate_limit(key: str, max_requests: int, window_seconds: int) -> bool:
    now = time()
    timestamps = _RATE_LIMIT_STORE.get(key, [])

    timestamps = [t for t in timestamps if now - t < window_seconds]

    if len(timestamps) >= max_requests:
        _RATE_LIMIT_STORE[key] = timestamps
        return False

    timestamps.append(now)
    _RATE_LIMIT_STORE[key] = timestamps
    return True