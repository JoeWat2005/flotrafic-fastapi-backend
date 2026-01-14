import stripe
from app.core.config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

PRO_PRICE_ID = settings.STRIPE_PRO_PRICE_ID

TIERS = {
    "free": {
        "enquiries": True,
        "bookings": True,
        "autopilot": False,
    },
    "pro": {
        "enquiries": True,
        "bookings": True,
        "autopilot": True,
    },
}