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


#Central API router aggregating all application routes
api_router = APIRouter()


#Authentication routes for businesses and administrators
api_router.include_router(auth.router)
api_router.include_router(admin_auth.router)


#Authenticated business routes for core product features
api_router.include_router(enquiries.router)
api_router.include_router(bookings.router)
api_router.include_router(customisation.router)
api_router.include_router(me.router)


#Public, unauthenticated routes used by customer-facing websites
api_router.include_router(public.router)


#Billing and Stripe-related routes
api_router.include_router(billing.router)
api_router.include_router(stripe_webhook.router)


#Admin-only routes for platform management
api_router.include_router(business.router)