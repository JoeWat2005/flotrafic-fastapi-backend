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

#auth routes
api_router.include_router(auth.router)
api_router.include_router(admin_auth.router)

#business routes
api_router.include_router(enquiries.router)
api_router.include_router(bookings.router)
api_router.include_router(customisation.router)
api_router.include_router(me.router)

#public routes
api_router.include_router(public.router)

#stripe routes
api_router.include_router(billing.router)
api_router.include_router(stripe_webhook.router)

#admin-only routes
api_router.include_router(business.router)