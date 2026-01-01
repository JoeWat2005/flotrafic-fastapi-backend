from fastapi import APIRouter
from app.api.routes import enquiries, bookings, business

api_router = APIRouter()
api_router.include_router(enquiries.router)
api_router.include_router(bookings.router)
api_router.include_router(business.router)
