from fastapi import APIRouter

from app.api.routes import (
    auth,
    admin_auth,
    enquiries,
    bookings,
    business,
    contact,
    me,
)

api_router = APIRouter()

# 🔓 Business / public auth
api_router.include_router(auth.router)
api_router.include_router(enquiries.router)
api_router.include_router(bookings.router)
api_router.include_router(contact.router)

# 👤 Business self-service
api_router.include_router(me.router)

# 🔒 Admin-only
api_router.include_router(admin_auth.router)
api_router.include_router(business.router)
