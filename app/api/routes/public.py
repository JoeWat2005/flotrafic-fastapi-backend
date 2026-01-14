from fastapi import APIRouter, Depends, HTTPException, Body, Request
from sqlalchemy.orm import Session

from app.db.models import Business, Enquiry, Visit, Booking
from app.db.session import get_db
from app.core.config import RESERVED_SLUGS
from app.schemas.enquiry import EnquiryCreate
from app.services.email import send_enquiry_notification, send_booking_pending_business, send_booking_pending_customer
from app.schemas.booking import PublicBookingCreate
from app.services.audit import log_action
from app.core.security import rate_limit, make_key
from app.core.utils import get_cached_business, set_cached_business

router = APIRouter(
    prefix="/public",
    tags=["Public"],
)
"""
PUBLIC ROUTES => NO FEATURE GATING OR BUSINESS AUTH

INSTEAD:

1) PUBLIC/BUSINESS => USES CACHING
2) PUBLIC/ENQUIRY => RATE LIMIT OF 5 REQUESTS / IP / BUSINESS / 10 MINUTES
3) PUBLIC/BOOKING => RATE LIMIT OF 5 REQUESTS / IP / BUSINESS / 10 MINUTES
4) PUBLIC/VISIT => RATE LIMIT OF 30 REQUESTS / IP / BUSINESS / 1 MINUTE (OVER THIS IGNORED)

"""

#get public business info
@router.get("/business")
def get_public_business(
    slug: str,
    db: Session = Depends(get_db),
):
    if slug in RESERVED_SLUGS:
        raise HTTPException(status_code=404, detail="Business not found")

    cached = get_cached_business(slug)
    if cached:
        return cached

    business = (
        db.query(Business)
        .filter(Business.slug == slug)
        .first()
    )

    if not business or not business.is_active:
        raise HTTPException(status_code=404, detail="Business not found")

    cust = business.customisation

    response_data = {
        "id": business.id,
        "name": business.name,
        "slug": business.slug,
        "customisation": {
            "primary_color": cust.primary_color if cust else "#000000",
            "secondary_color": cust.secondary_color if cust else "#ffffff",
            "accent_color": cust.accent_color if cust else "#2563eb",
            "logo_url": cust.logo_url if cust else None,
            "font_family": cust.font_family if cust else "Inter",

            "hero_title": cust.hero_title if cust else "Professional services you can trust",
            "hero_subtitle": cust.hero_subtitle if cust else "Get in touch today for a fast response",
            "cta_text": cust.cta_text if cust else "Request a quote",

            "about_title": cust.about_title if cust else None,
            "about_content": cust.about_content if cust else None,

            "contact_email": cust.contact_email if cust else None,
            "contact_phone": cust.contact_phone if cust else None,
            "contact_address": cust.contact_address if cust else None,

            "social_facebook": cust.social_facebook if cust else None,
            "social_twitter": cust.social_twitter if cust else None,
            "social_instagram": cust.social_instagram if cust else None,
            "social_linkedin": cust.social_linkedin if cust else None,

            "show_enquiry_form": cust.show_enquiry_form if cust else True,
            "show_pricing": cust.show_pricing if cust else False,
            "show_testimonials": cust.show_testimonials if cust else False,

            "testimonials": cust.testimonials if cust else [],
            "pricing_plans": cust.pricing_plans if cust else [],

            "border_radius": cust.border_radius if cust else "medium",
            "text_alignment": cust.text_alignment if cust else "center",
            "button_style": cust.button_style if cust else "solid",

            "section_order": cust.section_order if cust else [
                "hero", "about", "testimonials", "pricing", "contact"
            ],
            "animation_enabled": cust.animation_enabled if cust else True,
        }
    }

    set_cached_business(slug, response_data)

    return response_data

#public customer enquiry creation
@router.post("/enquiry")
def create_public_enquiry(
    slug: str,
    payload: EnquiryCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    key = make_key(slug, request, "enquiry")
    if not rate_limit(key, max_requests=5, window_seconds=600):
        raise HTTPException(status_code=429, detail="Too many enquiries")

    business = (
        db.query(Business)
        .filter(Business.slug == slug)
        .first()
    )

    if not business or not business.is_active:
        raise HTTPException(status_code=404, detail="Business not found")

    enquiries_enabled = True
    if business.customisation:
        enquiries_enabled = business.customisation.show_enquiry_form

    if not enquiries_enabled:
        raise HTTPException(status_code=400, detail="Enquiries are disabled")

    enquiry = Enquiry(
        name=payload.name,
        email=payload.email,
        message=payload.message,
        business_id=business.id,
        status="new",
        is_read=False,
    )

    db.add(enquiry)
    db.commit()
    db.refresh(enquiry)

    log_action(
        db=db,
        actor_type="system",
        actor_id=business.id,
        action="public.enquiry_created",
        details=f"enquiry_id={enquiry.id}",
    )

    send_enquiry_notification(
        business_email=business.email,
        business_name=business.name,
        customer_name=payload.name,
        customer_email=payload.email,
        message=payload.message,
    )

    return {"success": True}

#track website visits
@router.post("/visit")
def track_visit(
    payload: dict = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
):
    slug = payload.get("slug")
    if not slug:
        return {"success": False}

    key = make_key(slug, request, "visit")
    if not rate_limit(key, max_requests=30, window_seconds=60):
        return {"success": True}

    business = db.query(Business).filter(Business.slug == slug).first()
    if not business:
        return {"success": False}

    visit = Visit(
        business_id=business.id,
        path=payload.get("path", "/"),
        user_agent=payload.get("user_agent"),
    )
    db.add(visit)
    db.commit()

    return {"success": True}

#public customer booking creation
@router.post("/booking")
def create_public_booking(
    slug: str,
    payload: PublicBookingCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    key = make_key(slug, request, "booking")
    if not rate_limit(key, max_requests=5, window_seconds=600):
        raise HTTPException(status_code=429, detail="Too many booking attempts")

    business = (
        db.query(Business)
        .filter(Business.slug == slug, Business.is_active == True)
        .first()
    )

    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    conflict = (
        db.query(Booking)
        .filter(
            Booking.business_id == business.id,
            Booking.start_time < payload.end_time,
            Booking.end_time > payload.start_time,
        )
        .first()
    )

    if conflict:
        raise HTTPException(status_code=400, detail="Time slot unavailable")

    booking = Booking(
        business_id=business.id,
        start_time=payload.start_time,
        end_time=payload.end_time,
        status="pending",
    )

    db.add(booking)
    db.commit()
    db.refresh(booking)

    log_action(
        db=db,
        actor_type="system",
        actor_id=business.id,
        action="public.booking_requested",
        details=f"booking_id={booking.id}",
    )

    send_booking_pending_business(
        business_email=business.email,
        business_name=business.name,
        customer_email=payload.customer_email,
        start_time=payload.start_time,
    )

    send_booking_pending_customer(
        customer_email=payload.customer_email,
        business_name=business.name,
        start_time=payload.start_time,
    )

    return {"success": True}