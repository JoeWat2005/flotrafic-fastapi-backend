from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
import requests
from fastapi import HTTPException
from time import time

from app.core.config import settings

SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
_RATE_LIMIT_STORE = {}

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)

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

    # 🔍 DEBUG (TEMPORARY)
    print("Turnstile verification response:", data)

    if not data.get("success"):
        raise HTTPException(
            status_code=400,
            detail=f"Captcha verification failed: {data}",
        )
    
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

def make_key(slug: str, request, endpoint: str) -> str:
    ip = request.client.host if request.client else "unknown"
    return f"{slug}:{endpoint}:{ip}"