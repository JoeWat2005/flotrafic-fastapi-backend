from pydantic_settings import BaseSettings
from pydantic import Field
import re
from datetime import datetime, timedelta, timezone

"""
API CONFIGURATION
"""


#Class to load and read backend .env
class Settings(BaseSettings):

    FRONTEND_URL: str = "http://localhost:5173"
    
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")

    BREVO_API_KEY: str | None = None

    STRIPE_SECRET_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    STRIPE_PRO_PRICE_ID: str

    TURNSTILE_SECRET_KEY: str

    ADMIN_PASSWORD: str

    DATABASE_URL: str | None = None

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

STRIPE_GRACE_PERIOD_DAYS = 7

def apply_subscription_state(business, stripe_status: str | None = None):
    # Canonical Access Logic
    now = datetime.now(timezone.utc)
    
    # 1. Access Rule: Invoice-Driven
    # If the user has paid for time that covers now, they have access.
    invoice_covers_now = False
    if business.latest_paid_period_end and business.latest_paid_period_end > now:
        invoice_covers_now = True

    # 2. Fallback Rule: Subscription Status
    # If invoice data is missing/stale but subscription is demonstrably active and not ended.
    # Note: "canceled" status means it's over (unless invoice covers it). 
    # "past_due" usually means grace period or retry, we treat as active for access until fully canceled/unpaid.
    current_status = stripe_status if stripe_status else business.stripe_subscription_status
    sub_is_live = (
        current_status in ("active", "trialing", "past_due")
        and not business.stripe_ended_at  # Must not be hard-ended
    )
    
    has_pro_access = invoice_covers_now or sub_is_live

    # Update Tier & Active Flags
    if has_pro_access:
        business.tier = "pro"
        business.is_active = True
        business.grace_period_ends_at = None
    else:
        business.tier = "free"
        business.is_active = True
        business.grace_period_ends_at = None



#Acccount subscription tiers
TIERS = {
    "free": {
        "enquiries": True,
        "bookings": True,
        "customisation": True,
        "autopilot": False,
    },
    "pro": {
        "enquiries": True,
        "bookings": True,
        "customisation": True,
        "autopilot": True,
    },
}


#Slugs reserved for business logic 
RESERVED_SLUGS = {


    #Core infrastructure
    "www",
    "api",
    "admin",
    "static",
    "assets",
    "cdn",
    "files",


    #Backend route prefixes
    "auth",
    "billing",
    "bookings",
    "business",
    "enquiries",
    "me",
    "public",
    "stripe",


    #Frontend / platform routes
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


#Public route rate limits for public.py and auth
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


_PUBLIC_BUSINESS_CACHE = {}
TIME_TO_LIVE = 60

PASSWORD_REGEX = re.compile(
    r"^(?=.*[0-9])(?=.*[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]).{8,}$"
)