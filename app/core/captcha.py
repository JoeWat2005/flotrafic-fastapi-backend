import os
import requests
from fastapi import HTTPException

TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY")

if not TURNSTILE_SECRET_KEY:
    raise RuntimeError("TURNSTILE_SECRET_KEY not set")


def verify_captcha(token: str):
    res = requests.post(
        "https://challenges.cloudflare.com/turnstile/v0/siteverify",
        data={
            "secret": TURNSTILE_SECRET_KEY,
            "response": token,
        },
        timeout=5,
    )

    data = res.json()

    if not data.get("success"):
        raise HTTPException(
            status_code=400,
            detail="Captcha verification failed",
        )
