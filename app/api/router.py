from fastapi import APIRouter
from app.api.routes import enquiries, bookings

api_router = APIRouter()
api_router.include_router(enquiries.router)
api_router.include_router(bookings.router)
