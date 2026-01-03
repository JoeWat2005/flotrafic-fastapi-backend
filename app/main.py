from dotenv import load_dotenv
load_dotenv()  # 🔑 LOAD .env FIRST

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.db import models  # noqa: F401 (ensures models are registered)
from app.api.router import api_router
from app.db.seed import seed_business, seed_admin


app = FastAPI(title="Flotrafic API")


# ✅ CORS (DEV + PROD)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",     # Vite dev
        "http://127.0.0.1:5173",     # Alt localhost
        "https://flotrafic.co.uk",   # Prod
        "https://www.flotrafic.co.uk",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Create tables
Base.metadata.create_all(bind=engine)


@app.on_event("startup")
def startup():
    db = SessionLocal()
    try:
        seed_business(db)
        seed_admin(db)
    finally:
        db.close()


app.include_router(api_router)
