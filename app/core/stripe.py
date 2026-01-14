import stripe
from app.core.config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

FOUNDATION_PRICE_ID = settings.STRIPE_FOUNDATION_PRICE_ID
MANAGED_PRICE_ID = settings.STRIPE_MANAGED_PRICE_ID
AUTOPILOT_PRICE_ID = settings.STRIPE_AUTOPILOT_PRICE_ID

TIERS = {
    "foundation": {
        "enquiries_manage": False,
        "bookings": False,
        "ai_calls": False,
    },
    "managed": {
        "enquiries_manage": True,
        "bookings": True,
        "ai_calls": False,
    },
    "autopilot": {
        "enquiries_manage": True,
        "bookings": True,
        "ai_calls": True,
    },
}