import requests
from fastapi import HTTPException
from app.core.config import settings


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
