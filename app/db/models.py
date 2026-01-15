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
    Text,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, backref
from app.db.base import Base


# =========================================================
# SHARED ENUMS (centralised to avoid duplication issues):
# =========================================================


#Subscription tier for a business account
TierEnum = Enum("free", "pro", name="tier_enum")


#Stripe subscription lifecycle status
SubscriptionStatusEnum = Enum(
    "active",
    "trialing",
    "past_due",
    "canceled",
    "incomplete",
    name="subscription_status_enum",
)


#Workflow state for customer enquiries
EnquiryStatusEnum = Enum("new", "in_progress", "resolved", name="enquiry_status_enum")


#Actor type used in audit logging
ActorTypeEnum = Enum("system", "business", "admin", name="actor_type_enum")


#Lifecycle state for bookings
BookingStatusEnum = Enum(
    "pending", "confirmed", "cancelled", name="booking_status_enum"
)


# =========================================================
# BUSINESS (core account entity):
# =========================================================


#Represents a registered business account
class Business(Base):
    __tablename__ = "businesses"

    #Primary business identity fields
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    slug = Column(String, unique=True, nullable=False, index=True)

    #Subscription and access control
    tier = Column(TierEnum, nullable=False, default="free")
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    #Stripe subscription metadata
    stripe_customer_id = Column(String, nullable=True, index=True)
    stripe_subscription_id = Column(String, nullable=True, index=True)
    stripe_subscription_status = Column(SubscriptionStatusEnum, nullable=True)
    stripe_current_period_end = Column(DateTime(timezone=True), nullable=True)

    #Email verification state
    email_verified = Column(Boolean, nullable=False, default=False)
    email_verification_code = Column(String, nullable=True, index=True)
    email_verification_expires = Column(DateTime(timezone=True), nullable=True)

    #Password reset state
    password_reset_code = Column(String, nullable=True, index=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)

    #Relationships to dependent resources
    enquiries = relationship("Enquiry", back_populates="business", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="business", cascade="all, delete-orphan")
    customisation = relationship(
        "BusinessCustomisation",
        uselist=False,
        back_populates="business",
        cascade="all, delete-orphan",
    )


# =========================================================
# ENQUIRIES (customer messages / leads):
# =========================================================


#Represents a customer enquiry submitted to a business
class Enquiry(Base):
    __tablename__ = "enquiries"

    #Customer-provided enquiry details
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, index=True)
    message = Column(String, nullable=False)

    #Workflow state and read tracking
    status = Column(EnquiryStatusEnum, nullable=False, default="new")
    is_read = Column(Boolean, nullable=False, default=False)

    #Timestamp of submission
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    #Owning business
    business_id = Column(
        Integer,
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    business = relationship("Business", back_populates="enquiries")

    #Bookings optionally created from this enquiry
    bookings = relationship("Booking", back_populates="enquiry", cascade="all, delete-orphan")


# =========================================================
# BOOKINGS (appointments / scheduling):
# =========================================================


class Booking(Base):
    __tablename__ = "bookings"

    #Foreign keys to business and optional enquiry
    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    enquiry_id = Column(Integer, ForeignKey("enquiries.id", ondelete="SET NULL"), nullable=True, index=True)

    #Scheduled booking time window
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)

    #Optional notes for internal and customer use
    business_note = Column(Text, nullable=True)
    customer_note = Column(Text, nullable=True)

    #Booking lifecycle status
    status = Column(BookingStatusEnum, nullable=False, default="pending")

    #Creation timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    business = relationship("Business", back_populates="bookings")
    enquiry = relationship("Enquiry", back_populates="bookings")

    #Constraints to ensure booking validity and prevent duplicates
    __table_args__ = (
        Index("ix_booking_business_time", "business_id", "start_time", "end_time"),
        CheckConstraint("end_time > start_time", name="ck_booking_time_valid"),
        UniqueConstraint("enquiry_id", name="ud_booking_enquiry"),
    )


# =========================================================
# CONTACT MESSAGES (site-level contact form):
# =========================================================


class ContactMessage(Base):
    __tablename__ = "contact_messages"

    #Contact form submission details
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, index=True)
    message = Column(String, nullable=False)

    #Optional metadata for moderation and analytics
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# =========================================================
# ADMINS (platform administrators):
# =========================================================


#Represents an administrator with elevated privileges
class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)


# =========================================================
# AUDIT LOGS (immutable security trail):
# =========================================================


#Immutable audit log entry for security-sensitive actions
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    actor_type = Column(ActorTypeEnum, nullable=False)
    actor_id = Column(Integer, nullable=True, index=True)
    action = Column(String, nullable=False)
    details = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


# =========================================================
# VISITS (anonymous analytics):
# =========================================================


#Represents a single anonymous website visit
class Visit(Base):
    __tablename__ = "visits"

    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)

    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    path = Column(String, nullable=False, default="/")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


# =========================================================
# BUSINESS CUSTOMISATION (public website settings):
# =========================================================


#Customisable website appearance and content for a business
class BusinessCustomisation(Base):
    __tablename__ = "business_customisations"

    #One-to-one link with business
    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    #Branding and typography
    primary_color = Column(String, nullable=False, default="#000000")
    secondary_color = Column(String, nullable=False, default="#ffffff")
    accent_color = Column(String, nullable=False, default="#2563eb")
    logo_path = Column(String, nullable=True)
    favicon_url = Column(String, nullable=True)
    font_family = Column(String, nullable=False, default="Inter")

    #Hero and call-to-action content
    hero_title = Column(String, nullable=False, default="Professional services you can trust")
    hero_subtitle = Column(String, nullable=False, default="Get in touch today for a fast response")
    cta_text = Column(String, nullable=False, default="Request a quote")

    #Feature toggles controlling visible sections
    show_enquiry_form = Column(Boolean, nullable=False, default=True)
    show_testimonials = Column(Boolean, nullable=False, default=False)
    show_pricing = Column(Boolean, nullable=False, default=False)
    animation_enabled = Column(Boolean, nullable=False, default=True)

    #Advanced styling overrides
    custom_css = Column(String, nullable=True)

    #Layout and component styling
    border_radius = Column(String, nullable=False, default="medium")
    text_alignment = Column(String, nullable=False, default="center")
    button_style = Column(String, nullable=False, default="solid")

    #About section content
    about_title = Column(String, nullable=True)
    about_content = Column(String, nullable=True)

    #Contact information
    contact_email = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)
    contact_address = Column(String, nullable=True)

    #Social media links
    social_facebook = Column(String, nullable=True)
    social_twitter = Column(String, nullable=True)
    social_instagram = Column(String, nullable=True)
    social_linkedin = Column(String, nullable=True)

    #Dynamic content lists
    testimonials = Column(JSON, nullable=False, default=list)
    pricing_plans = Column(JSON, nullable=False, default=list)

    #Ordered list of page sections
    section_order = Column(
        JSON,
        nullable=False,
        default=lambda: ["hero", "about", "testimonials", "pricing", "contact"],
    )

    business = relationship("Business", back_populates="customisation")


# =========================================================
# BUSINESS AVAILABILITY (booking rules):
# =========================================================


#Defines availability and scheduling rules for a business
class BusinessAvailability(Base):
    __tablename__ = "business_availability"

    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), unique=True, nullable=False)

    #Weekly opening hours configuration
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

    #Slot configuration and automation behaviour
    slot_length_minutes = Column(Integer, nullable=False, default=60)
    buffer_minutes = Column(Integer, nullable=False, default=30)
    auto_confirm = Column(Boolean, nullable=False, default=True)

    #Global availability state and timezone
    closed = Column(Boolean, nullable=False, default=False)
    timezone = Column(String, nullable=False, default="Europe/London")

    business = relationship("Business", backref=backref("availability", uselist=False))


# =========================================================
# STRIPE EVENTS (webhook deduplication)
# =========================================================


#Tracks processed Stripe webhook events to ensure idempotency
class StripeEvent(Base):
    __tablename__ = "stripe_events"

    event_id = Column(String, primary_key=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)