from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

from app.core.config import settings

db_url = settings.DATABASE_URL

#create db engine
engine = create_engine(
    db_url,
    connect_args={"check_same_thread": False},
)

#db connection manager
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

#access database
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()