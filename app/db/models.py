from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Boolean,
    Enum,
    Index,
    JSON,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, backref
from app.db.base import Base


# =========================================================
# SHARED ENUMS (avoid duplication issues)
# =========================================================
TierEnum = Enum(
    "foundation",
    "managed",
    "autopilot",
    name="tier_enum",
)

SubscriptionStatusEnum = Enum(
    "active",
    "trialing",
    "past_due",
    "canceled",
    "incomplete",
    name="subscription_status_enum",
)

EnquiryStatusEnum = Enum(
    "new",
    "in_progress",
    "resolved",
    name="enquiry_status_enum",
)

ActorTypeEnum = Enum(
    "system",
    "business",
    "admin",
    name="actor_type_enum",
)

BookingStatusEnum = Enum(
    "pending",
    "confirmed",
    "cancelled",
    name="booking_status_enum",
)


# =========================================================
# BUSINESS
# =========================================================
class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True)

    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    slug = Column(String, unique=True, nullable=False, index=True)

    tier = Column(TierEnum, nullable=False, default="foundation")

    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    # Stripe
    stripe_customer_id = Column(String, nullable=True, index=True)
    stripe_subscription_id = Column(String, nullable=True, index=True)
    stripe_subscription_status = Column(SubscriptionStatusEnum, nullable=True)
    stripe_current_period_end = Column(DateTime(timezone=True), nullable=True)

    # Email verification
    email_verified = Column(Boolean, nullable=False, default=False)
    email_verification_code = Column(String, nullable=True, index=True)
    email_verification_expires = Column(DateTime(timezone=True), nullable=True)

    # Password reset
    password_reset_code = Column(String, nullable=True, index=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)

    enquiries = relationship(
        "Enquiry",
        back_populates="business",
        cascade="all, delete-orphan",
    )

    bookings = relationship(
        "Booking",
        back_populates="business",
        cascade="all, delete-orphan",
    )

    customisation = relationship(
        "BusinessCustomisation",
        uselist=False,
        back_populates="business",
        cascade="all, delete-orphan",
    )


# =========================================================
# ENQUIRIES
# =========================================================
class Enquiry(Base):
    __tablename__ = "enquiries"

    id = Column(Integer, primary_key=True)

    name = Column(String, nullable=False)
    email = Column(String, nullable=False, index=True)
    message = Column(String, nullable=False)

    status = Column(EnquiryStatusEnum, nullable=False, default="new")
    is_read = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    business_id = Column(
        Integer,
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    business = relationship("Business", back_populates="enquiries")

    bookings = relationship(
        "Booking",
        back_populates="enquiry",
        cascade="all, delete-orphan",
    )


# =========================================================
# BOOKINGS
# =========================================================
class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True)

    business_id = Column(
        Integer,
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    enquiry_id = Column(
        Integer,
        ForeignKey("enquiries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)

    status = Column(BookingStatusEnum, nullable=False, default="pending")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    business = relationship("Business", back_populates="bookings")
    enquiry = relationship("Enquiry", back_populates="bookings")

    __table_args__ = (
        Index(
            "ix_booking_business_time",
            "business_id",
            "start_time",
            "end_time",
        ),
        CheckConstraint(
            "end_time > start_time",
            name="ck_booking_time_valid",
        ),
        UniqueConstraint(
            "enquiry_id",
            name="ud_booking_enquiry",
        )
    )


# =========================================================
# CONTACT MESSAGES
# =========================================================
class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, index=True)
    message = Column(String, nullable=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# =========================================================
# ADMINS
# =========================================================
class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)


# =========================================================
# AUDIT LOGS
# =========================================================
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)

    actor_type = Column(ActorTypeEnum, nullable=False)
    actor_id = Column(Integer, nullable=True, index=True)

    action = Column(String, nullable=False)
    details = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


# =========================================================
# VISITS
# =========================================================
class Visit(Base):
    __tablename__ = "visits"

    id = Column(Integer, primary_key=True)

    business_id = Column(
        Integer,
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    path = Column(String, nullable=False, default="/")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


# =========================================================
# BUSINESS CUSTOMISATION
# =========================================================
class BusinessCustomisation(Base):
    __tablename__ = "business_customisations"

    id = Column(Integer, primary_key=True)

    business_id = Column(
        Integer,
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Branding
    primary_color = Column(String, nullable=False, default="#000000")
    secondary_color = Column(String, nullable=False, default="#ffffff")
    accent_color = Column(String, nullable=False, default="#2563eb")

    logo_path = Column(String, nullable=True)
    favicon_url = Column(String, nullable=True)
    font_family = Column(String, nullable=False, default="Inter")

    # Content
    hero_title = Column(String, nullable=False, default="Professional services you can trust")
    hero_subtitle = Column(String, nullable=False, default="Get in touch today for a fast response")
    cta_text = Column(String, nullable=False, default="Request a quote")

    # Feature toggles
    show_enquiry_form = Column(Boolean, nullable=False, default=True)
    show_testimonials = Column(Boolean, nullable=False, default=False)
    show_pricing = Column(Boolean, nullable=False, default=False)
    animation_enabled = Column(Boolean, nullable=False, default=True)

    # Advanced overrides
    custom_css = Column(String, nullable=True)

    # Layout / style
    border_radius = Column(String, nullable=False, default="medium")
    text_alignment = Column(String, nullable=False, default="center")
    button_style = Column(String, nullable=False, default="solid")

    # About
    about_title = Column(String, nullable=True)
    about_content = Column(String, nullable=True)

    # Contact info
    contact_email = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)
    contact_address = Column(String, nullable=True)

    # Socials
    social_facebook = Column(String, nullable=True)
    social_twitter = Column(String, nullable=True)
    social_instagram = Column(String, nullable=True)
    social_linkedin = Column(String, nullable=True)

    # Lists
    testimonials = Column(JSON, nullable=False, default=list)
    pricing_plans = Column(JSON, nullable=False, default=list)

    # Layout order
    section_order = Column(
        JSON,
        nullable=False,
        default=lambda: ["hero", "about", "testimonials", "pricing", "contact"],
    )

    business = relationship("Business", back_populates="customisation")


# =========================================================
# BUSINESS AVAILABILITY
# =========================================================
class BusinessAvailability(Base):
    __tablename__ = "business_availability"

    id = Column(Integer, primary_key=True)

    business_id = Column(
        Integer,
        ForeignKey("businesses.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    opening_hours = Column(
        JSON,
        nullable=False,
        default=lambda: {
            "0": {"start": "09:00", "end": "17:00"},
            "1": {"start": "09:00", "end": "17:00"},
            "2": {"start": "09:00", "end": "17:00"},
            "3": {"start": "09:00", "end": "17:00"},
            "4": {"start": "09:00", "end": "17:00"},
            "5": None,
            "6": None,
        },
    )

    slot_length_minutes = Column(Integer, nullable=False, default=60)
    buffer_minutes = Column(Integer, nullable=False, default=30)
    auto_confirm = Column(Boolean, nullable=False, default=True)

    closed = Column(Boolean, nullable=False, default=False)
    timezone = Column(String, nullable=False, default="Europe/London")

    business = relationship(
        "Business",
        backref=backref("availability", uselist=False),
    )

