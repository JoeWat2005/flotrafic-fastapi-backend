from dotenv import load_dotenv
load_dotenv()  # 🔑 LOAD .env FIRST

from fastapi import FastAPI

from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.db import models  # noqa: F401 (ensures models are registered)
from app.api.router import api_router
from app.db.seed import seed_business


app = FastAPI(title="Flotrafic API")


# Create tables
Base.metadata.create_all(bind=engine)


@app.on_event("startup")
def startup():
    db = SessionLocal()
    try:
        seed_business(db)
    finally:
        db.close()


app.include_router(api_router)
