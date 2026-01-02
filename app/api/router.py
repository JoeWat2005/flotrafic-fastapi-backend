from fastapi import APIRouter

from app.api.routes import enquiries, bookings, business, auth, contact, admin_auth

api_router = APIRouter()

# 🔓 Public / business-auth routes
api_router.include_router(auth.router)
api_router.include_router(enquiries.router)
api_router.include_router(bookings.router)
api_router.include_router(contact.router)

# 🔒 Admin-only routes
# Admin auth is enforced INSIDE the router itself
api_router.include_router(business.router)
api_router.include_router(admin_auth.router)
