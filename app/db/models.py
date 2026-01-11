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
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


# =========================================================
# BUSINESS
# =========================================================
class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True)

    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    slug = Column(String, unique=True, nullable=False, index=True)

    tier = Column(
        Enum(
            "foundation",
            "managed",
            "autopilot",
            name="tier_enum",
        ),
        nullable=False,
    )

    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    # Stripe
    stripe_customer_id = Column(String, nullable=True, index=True)
    stripe_subscription_id = Column(String, nullable=True, index=True)
    stripe_subscription_status = Column(String, nullable=True)
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
    email = Column(String, nullable=False)
    message = Column(String, nullable=False)

    status = Column(
        Enum(
            "new",
            "in_progress",
            "resolved",
            name="enquiry_status_enum",
        ),
        nullable=False,
        default="new",
    )

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
    )


# =========================================================
# CONTACT MESSAGES
# =========================================================
class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
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

    actor_type = Column(
        Enum(
            "system",
            "business",
            "admin",
            name="actor_type_enum",
        ),
        nullable=False,
    )

    actor_id = Column(Integer, nullable=False, index=True)
    action = Column(String, nullable=False)
    details = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

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

    # =========================
    # Branding
    # =========================
    primary_color = Column(String, default="#000000")      # Black
    secondary_color = Column(String, default="#ffffff")    # White
    accent_color = Column(String, default="#2563eb")       # Blue-600

    logo_url = Column(String, nullable=True)
    favicon_url = Column(String, nullable=True)

    font_family = Column(String, default="Inter")

    # =========================
    # Content
    # =========================
    hero_title = Column(String, default="Professional services you can trust")
    hero_subtitle = Column(String, default="Get in touch today for a fast response")
    cta_text = Column(String, default="Request a quote")

    # =========================
    # Feature toggles
    # =========================
    show_enquiry_form = Column(Boolean, default=True)
    show_testimonials = Column(Boolean, default=False)
    show_pricing = Column(Boolean, default=False)

    # =========================
    # Advanced overrides
    # =========================
    custom_css = Column(String, nullable=True)

    # =========================
    # Style
    # =========================
    border_radius = Column(String, default="medium")
    text_alignment = Column(String, default="center")
    button_style = Column(String, default="solid")
    
    # =========================
    # New Content Properties
    # =========================
    about_title = Column(String, nullable=True)
    about_content = Column(String, nullable=True)

    # Contact Info
    contact_email = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)
    contact_address = Column(String, nullable=True)

    # Socials
    social_facebook = Column(String, nullable=True)
    social_twitter = Column(String, nullable=True)
    social_instagram = Column(String, nullable=True)
    social_linkedin = Column(String, nullable=True)

    # Lists (Testimonials & Pricing)
    testimonials = Column(JSON, default=list)
    pricing_plans = Column(JSON, default=list)
    
    # Layout Order
    section_order = Column(JSON, default=lambda: ["hero", "about", "testimonials", "pricing", "contact"])
    
    # Animations
    animation_enabled = Column(Boolean, default=True)

    business = relationship("Business", back_populates="customisation")
