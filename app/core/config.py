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

    STRIPE_FOUNDATION_PRICE_ID: str
    STRIPE_MANAGED_PRICE_ID: str
    STRIPE_AUTOPILOT_PRICE_ID: str
    STRIPE_SETUP_PRICE_ID: str | None = None

    # ------------------------------------------------------------------
    # Cloudflare Turnstile
    # ------------------------------------------------------------------
    TURNSTILE_SECRET_KEY: str

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
