from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Literal

"""
CUSTOMISATION ROUTE SCHEMA
"""

#testimonial
class Testimonial(BaseModel):
    name: str
    role: Optional[str] = None
    content: str
    rating: int = Field(default=5, ge=1, le=5)

#pricing
class PricingPlan(BaseModel):
    name: str
    price: str
    features: List[str] = Field(default_factory=list)
    is_popular: bool = False

#base customisation
class CustomisationBase(BaseModel):
    
    #branding
    primary_color: Optional[str] = "#0f172a"
    secondary_color: Optional[str] = "#334155"
    accent_color: Optional[str] = "#38bdf8"
    font_family: Optional[str] = "Inter"

    #hero /content
    hero_title: Optional[str] = "Professional services you can trust"
    hero_subtitle: Optional[str] = "Get in touch today for a fast response"
    cta_text: Optional[str] = "Request a quote"
    about_title: Optional[str] = None
    about_content: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_address: Optional[str] = None

    #social media links
    social_facebook: Optional[HttpUrl] = None
    social_twitter: Optional[HttpUrl] = None
    social_instagram: Optional[HttpUrl] = None
    social_linkedin: Optional[HttpUrl] = None

    #feature toggles
    show_enquiry_form: bool = True
    show_testimonials: bool = False
    show_pricing: bool = False

    #feature lists
    testimonials: List[Testimonial] = Field(default_factory=list)
    pricing_plans: List[PricingPlan] = Field(default_factory=list)

    #styling
    border_radius: Literal["none", "small", "medium", "large"] = "medium"
    text_alignment: Literal["left", "center", "right"] = "center"
    button_style: Literal["solid", "outline", "ghost"] = "solid"

    #default section order
    section_order: List[str] = Field(
        default_factory=lambda: [
            "hero",
            "about",
            "services",
            "testimonials",
            "pricing",
            "contact",
        ]
    )

    #animation toggle
    animation_enabled: bool = True

    #custom css
    custom_css: Optional[str] = None

#customisation update
class CustomisationUpdate(BaseModel):
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    accent_color: Optional[str] = None
    font_family: Optional[str] = None

    hero_title: Optional[str] = None
    hero_subtitle: Optional[str] = None
    cta_text: Optional[str] = None

    about_title: Optional[str] = None
    about_content: Optional[str] = None

    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_address: Optional[str] = None

    social_facebook: Optional[HttpUrl] = None
    social_twitter: Optional[HttpUrl] = None
    social_instagram: Optional[HttpUrl] = None
    social_linkedin: Optional[HttpUrl] = None

    show_enquiry_form: Optional[bool] = None
    show_testimonials: Optional[bool] = None
    show_pricing: Optional[bool] = None

    testimonials: Optional[List[Testimonial]] = None
    pricing_plans: Optional[List[PricingPlan]] = None

    border_radius: Optional[Literal["none", "small", "medium", "large"]] = None
    text_alignment: Optional[Literal["left", "center", "right"]] = None
    button_style: Optional[Literal["solid", "outline", "ghost"]] = None

    section_order: Optional[List[str]] = None
    animation_enabled: Optional[bool] = None
    custom_css: Optional[str] = None


class CustomisationOut(CustomisationBase):
    id: int
    business_id: int
    logo_path: Optional[str] = None

    model_config = {"from_attributes": True}

