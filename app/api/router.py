from fastapi import APIRouter, Depends

from app.api.routes import enquiries, bookings, business, auth, contact
from app.api.admin_deps import require_admin

api_router = APIRouter()

# 🔓 Public / business-auth routes
api_router.include_router(auth.router)
api_router.include_router(enquiries.router)
api_router.include_router(bookings.router)
api_router.include_router(contact.router)

# 🔒 Admin-only routes
api_router.include_router(
    business.router,
    dependencies=[Depends(require_admin)],
)
