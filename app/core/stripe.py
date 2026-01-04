import stripe
import os

# =========================
# STRIPE CONFIG (SINGLE SOURCE OF TRUTH)
# =========================

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
if not STRIPE_SECRET_KEY:
    raise RuntimeError("STRIPE_SECRET_KEY is not set")

stripe.api_key = STRIPE_SECRET_KEY


FOUNDATION_PRICE_ID = os.getenv("STRIPE_FOUNDATION_PRICE_ID")
MANAGED_PRICE_ID = os.getenv("STRIPE_MANAGED_PRICE_ID")
AUTOPILOT_PRICE_ID = os.getenv("STRIPE_AUTOPILOT_PRICE_ID")
SETUP_PRICE_ID = os.getenv("STRIPE_SETUP_PRICE_ID")

missing = [
    name for name, value in {
        "STRIPE_FOUNDATION_PRICE_ID": FOUNDATION_PRICE_ID,
        "STRIPE_MANAGED_PRICE_ID": MANAGED_PRICE_ID,
        "STRIPE_AUTOPILOT_PRICE_ID": AUTOPILOT_PRICE_ID,
        "STRIPE_SETUP_PRICE_ID": SETUP_PRICE_ID,
    }.items()
    if not value
]

if missing:
    raise RuntimeError(f"Missing Stripe env vars: {', '.join(missing)}")
