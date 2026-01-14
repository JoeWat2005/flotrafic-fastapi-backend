from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # ------------------------------------------------------------------
    # App
    # ------------------------------------------------------------------
    FRONTEND_URL: str = "http://localhost:5173"
    # ------------------------------------------------------------------
    # JWT
    # ------------------------------------------------------------------
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")

    # ------------------------------------------------------------------
    # Email (Brevo)
    # ------------------------------------------------------------------
    BREVO_API_KEY: str | None = None

    # ------------------------------------------------------------------
    # Stripe
    # ------------------------------------------------------------------
    STRIPE_SECRET_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    
    STRIPE_PRO_PRICE_ID: str

    # ------------------------------------------------------------------
    # Cloudflare Turnstile
    # ------------------------------------------------------------------
    TURNSTILE_SECRET_KEY: str

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

RESERVED_SLUGS = {
    # Core infrastructure
    "www",
    "api",
    "admin",
    "static",
    "assets",
    "cdn",
    "files",

    # Backend route prefixes
    "auth",
    "billing",
    "bookings",
    "business",
    "enquiries",
    "me",
    "public",
    "stripe",

    # Frontend / platform routes
    "dashboard",
    "login",
    "signup",
    "settings",
    "account",
    "pricing",
    "docs",
    "help",
    "support",
    "status",
}

RATE_LIMITS = {
    "login": (5, 60),
    "pre_register": (3, 60),
    "verify_email": (5, 60),
    "password_reset": (3, 60),
    "resend_verification": (2, 60),
    "request_password_reset": (2, 60),
    "reset_password": (5, 60),
    "enquiry": (5, 600),
    "booking": (5, 600),
    "visit": (30, 60),
}