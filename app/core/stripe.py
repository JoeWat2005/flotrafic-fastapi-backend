import stripe
import os

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

MANAGED_PRICE_ID = os.getenv("STRIPE_MANAGED_PRICE_ID")
AUTOPILOT_PRICE_ID = os.getenv("STRIPE_AUTOPILOT_PRICE_ID")
