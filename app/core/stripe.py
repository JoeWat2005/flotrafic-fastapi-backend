import stripe
from app.core.config import settings

# =========================
# STRIPE CONFIG (SINGLE SOURCE OF TRUTH)
# =========================

stripe.api_key = settings.STRIPE_SECRET_KEY

FOUNDATION_PRICE_ID = settings.STRIPE_FOUNDATION_PRICE_ID
MANAGED_PRICE_ID = settings.STRIPE_MANAGED_PRICE_ID
AUTOPILOT_PRICE_ID = settings.STRIPE_AUTOPILOT_PRICE_ID

