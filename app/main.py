from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.db import models  # noqa: F401 (ensures models are registered)
from app.api.router import api_router
from app.db.seed import seed_admin


#Create application instance
app = FastAPI(title="Flotrafic API")


#Serve uploaded media files via static route
app.mount("/media", StaticFiles(directory="uploads"), name="media")


#configure CORS for local development and production frontend domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://site.flotrafic.local:5173",
        "https://flotrafic.co.uk",
        "https://www.flotrafic.co.uk",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


#Create all database tables on application startup
Base.metadata.create_all(bind=engine)


#Seed initial admin account when the application starts
@app.on_event("startup")
def startup():
    db = SessionLocal()
    try:
        seed_admin(db)
    finally:
        db.close()


#Register all API routes under the main application
app.include_router(api_router)