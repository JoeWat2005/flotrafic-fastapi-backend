from pydantic import BaseModel, HttpUrl
from typing import Optional, Any, List

class Testimonial(BaseModel):
    name: str
    role: Optional[str] = None
    content: str
    rating: int = 5

class PricingPlan(BaseModel):
    name: str
    price: str
    features: List[str] = []
    is_popular: bool = False

class CustomisationBase(BaseModel):
    # Branding
    primary_color: Optional[str] = "#0f172a"
    secondary_color: Optional[str] = "#334155"
    accent_color: Optional[str] = "#38bdf8"
    font_family: Optional[str] = "Inter"
    logo_url: Optional[str] = None
    
    # Content
    hero_title: Optional[str] = "Professional services you can trust"
    hero_subtitle: Optional[str] = "Get in touch today for a fast response"
    cta_text: Optional[str] = "Request a quote"
    
    about_title: Optional[str] = None
    about_content: Optional[str] = None
    
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_address: Optional[str] = None
    
    social_facebook: Optional[str] = None
    social_twitter: Optional[str] = None
    social_instagram: Optional[str] = None
    social_linkedin: Optional[str] = None
    
    # Features
    show_enquiry_form: Optional[bool] = True
    show_testimonials: Optional[bool] = False
    show_pricing: Optional[bool] = False
    
    testimonials: List[Testimonial] = []
    pricing_plans: List[PricingPlan] = []
    
    # Style
    border_radius: Optional[str] = "medium"
    text_alignment: Optional[str] = "center"
    button_style: Optional[str] = "solid"
    
    section_order: List[str] = ["hero", "about", "services", "testimonials", "pricing", "contact"]
    
    # Animations
    animation_enabled: Optional[bool] = True
    
    # Advanced
    custom_css: Optional[str] = None

class CustomisationUpdate(BaseModel):
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    accent_color: Optional[str] = None
    font_family: Optional[str] = None
    logo_url: Optional[str] = None
    
    hero_title: Optional[str] = None
    hero_subtitle: Optional[str] = None
    cta_text: Optional[str] = None
    
    about_title: Optional[str] = None
    about_content: Optional[str] = None
    
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_address: Optional[str] = None
    
    social_facebook: Optional[str] = None
    social_twitter: Optional[str] = None
    social_instagram: Optional[str] = None
    social_linkedin: Optional[str] = None
    
    show_enquiry_form: Optional[bool] = None
    show_testimonials: Optional[bool] = None
    show_pricing: Optional[bool] = None
    
    testimonials: Optional[List[Testimonial]] = None
    pricing_plans: Optional[List[PricingPlan]] = None
    
    border_radius: Optional[str] = None
    text_alignment: Optional[str] = None
    button_style: Optional[str] = None
    
    section_order: Optional[List[str]] = None
    
    animation_enabled: Optional[bool] = None
    
    custom_css: Optional[str] = None

class CustomisationOut(CustomisationBase):
    id: int
    business_id: int

    model_config = {
        "from_attributes": True
    }
