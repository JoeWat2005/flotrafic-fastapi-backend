from fastapi import APIRouter

from app.api.routes import (
    auth,
    admin_auth,
    enquiries,
    bookings,
    business,
    me,
    billing,
    stripe_webhook,
    public,
    customisation,
)

api_router = APIRouter()

# 🔓 Business / public auth
api_router.include_router(auth.router)
api_router.include_router(enquiries.router)
api_router.include_router(bookings.router)
api_router.include_router(public.router)

# 👤 Business self-service
api_router.include_router(me.router)
api_router.include_router(customisation.router)

# 🔒 Admin-only
api_router.include_router(admin_auth.router)
api_router.include_router(business.router)

api_router.include_router(billing.router)
api_router.include_router(stripe_webhook.router)
