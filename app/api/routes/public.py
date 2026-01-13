from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.db.models import Business, Enquiry, Visit, Booking
from app.db.session import get_db
from app.core.config import RESERVED_SLUGS
from app.schemas.enquiry import EnquiryCreate
from app.services.email import send_enquiry_notification, send_booking_pending_business, send_booking_pending_customer
from app.schemas.booking import PublicBookingCreate
from app.services.audit import log_action

router = APIRouter(
    prefix="/public",
    tags=["Public"],  # ✅ MUST be a list
)


@router.get("/business")
def get_public_business(
    slug: str,
    db: Session = Depends(get_db),
):
    if slug in RESERVED_SLUGS:
        raise HTTPException(status_code=404, detail="Business not found")

    business = (
        db.query(Business)
        .filter(Business.slug == slug)
        .first()
    )

    if not business or not business.is_active:
        raise HTTPException(status_code=404, detail="Business not found")

    # Get customisation or defaults
    cust = business.customisation
    
    # Defaults if no customisation record exists
    response_data = {
        "id": business.id,
        "name": business.name,
        "slug": business.slug,
        "customisation": {
            "primary_color": "#000000",
            "secondary_color": "#ffffff",
            "accent_color": "#2563eb",
            "logo_url": None,
            "font_family": "Inter",
            
            "hero_title": "Professional services you can trust",
            "hero_subtitle": "Get in touch today for a fast response",
            "cta_text": "Request a quote",
            
            "about_title": None,
            "about_content": None,
            
            "contact_email": None,
            "contact_phone": None,
            "contact_address": None,
            
            "social_facebook": None,
            "social_twitter": None,
            "social_instagram": None,
            "social_linkedin": None,
            
            "show_enquiry_form": True,
            "show_pricing": False,
            "show_testimonials": False,
            
            "testimonials": [],
            "pricing_plans": [],
            
            "border_radius": "medium",
            "text_alignment": "center",
            "button_style": "solid",
            
            "section_order": ["hero", "about", "testimonials", "pricing", "contact"],
            "animation_enabled": True,
        }
    }

    if cust:
        response_data["customisation"] = {
            "primary_color": cust.primary_color,
            "secondary_color": cust.secondary_color,
            "accent_color": cust.accent_color,
            "logo_url": cust.logo_url,
            "font_family": cust.font_family,
            
            "hero_title": cust.hero_title,
            "hero_subtitle": cust.hero_subtitle,
            "cta_text": cust.cta_text,
            
            "about_title": cust.about_title,
            "about_content": cust.about_content,
            
            "contact_email": cust.contact_email,
            "contact_phone": cust.contact_phone,
            "contact_address": cust.contact_address,
            
            "social_facebook": cust.social_facebook,
            "social_twitter": cust.social_twitter,
            "social_instagram": cust.social_instagram,
            "social_linkedin": cust.social_linkedin,
            
            "show_enquiry_form": cust.show_enquiry_form,
            "show_pricing": cust.show_pricing,
            "show_testimonials": cust.show_testimonials,
            
            "testimonials": cust.testimonials,
            "pricing_plans": cust.pricing_plans,
            
            "border_radius": cust.border_radius,
            "text_alignment": cust.text_alignment,
            "button_style": cust.button_style,
            
            "section_order": cust.section_order,
            "animation_enabled": cust.animation_enabled,
        }

    return response_data

@router.post("/enquiry")
def create_public_enquiry(
    slug: str,
    payload: EnquiryCreate,
    db: Session = Depends(get_db),
):
    # 1. Validate Business
    business = (
        db.query(Business)
        .filter(Business.slug == slug)
        .first()
    )

    if not business or not business.is_active:
        raise HTTPException(status_code=404, detail="Business not found")

    # 2. Check if enquiries are enabled for this business
    # If no customisation record, default is True (as per our default dict above)
    enquiries_enabled = True
    if business.customisation:
        enquiries_enabled = business.customisation.show_enquiry_form
    
    if not enquiries_enabled:
        raise HTTPException(status_code=400, detail="Enquiries are disabled for this business")

    # 3. Create Enquiry
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

    # 4. Send Email Notification
    send_enquiry_notification(
        business_email=business.email,
        business_name=business.name,
        customer_name=payload.name,
        customer_email=payload.email,
        message=payload.message,
    )


    return {"success": True, "message": "Enquiry sent successfully"}

@router.post("/visit")
def track_visit(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
):
    slug = payload.get("slug")
    if not slug:
        return {"success": False}
        
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

@router.post("/booking")
def create_public_booking(
    slug: str,
    payload: PublicBookingCreate,
    db: Session = Depends(get_db),
):
    business = (
        db.query(Business)
        .filter(Business.slug == slug, Business.is_active == True)
        .first()
    )

    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    # Overlap protection
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

    # Emails
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
