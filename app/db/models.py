from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base

class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    tier = Column(String, nullable=False)

    hashed_password = Column(String, nullable=False)


class Enquiry(Base):
    __tablename__ = "enquiries"

    id = Column(Integer, primary_key=True)

    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    message = Column(String, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_read = Column(Boolean, default=False)
    status = Column(String, default="new")

    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    business = relationship("Business")

    bookings = relationship(
        "Booking",
        back_populates="enquiry",
        cascade="all, delete-orphan",
    )


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True)

    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    enquiry_id = Column(Integer, ForeignKey("enquiries.id"), nullable=True)

    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    business = relationship("Business")
    enquiry = relationship("Enquiry", back_populates="bookings")
