from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.db.models import Business, Enquiry, BusinessCustomisation
from app.db.session import get_db
from app.core.config import RESERVED_SLUGS
from app.schemas.enquiry import EnquiryCreate

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
            "primary_color": "#0f172a",
            "secondary_color": "#334155",
            "accent_color": "#38bdf8",
            "logo_url": None,
            "font_family": "Inter",
            "hero_title": "Professional services you can trust",
            "hero_subtitle": "Get in touch today for a fast response",
            "cta_text": "Request a quote",
            "show_enquiry_form": True,
            "show_pricing": False,
            "show_testimonials": False,
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
            "show_enquiry_form": cust.show_enquiry_form,
            "show_pricing": cust.show_pricing,
            "show_testimonials": cust.show_testimonials,
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

    return {"success": True, "message": "Enquiry sent successfully"}

