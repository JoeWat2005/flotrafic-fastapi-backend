from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Literal

"""
CUSTOMISATION ROUTE SCHEMA
"""


#Single customer testimonial displayed on the public website
class Testimonial(BaseModel):
    name: str
    role: Optional[str] = None
    content: str
    rating: int = Field(default=5, ge=1, le=5)


#Pricing plan definition displayed on the public website
class PricingPlan(BaseModel):
    name: str
    price: str
    features: List[str] = Field(default_factory=list)
    is_popular: bool = False


#Base customisation model defining all configurable website settings
class CustomisationBase(BaseModel):

    #Brand colour and typography configuration
    primary_color: Optional[str] = "#0f172a"
    secondary_color: Optional[str] = "#334155"
    accent_color: Optional[str] = "#38bdf8"
    font_family: Optional[str] = "Inter"

    #Hero, about, and contact content displayed on the site
    hero_title: Optional[str] = "Professional services you can trust"
    hero_subtitle: Optional[str] = "Get in touch today for a fast response"
    cta_text: Optional[str] = "Request a quote"
    about_title: Optional[str] = None
    about_content: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_address: Optional[str] = None

    #Optional social media profile links
    social_facebook: Optional[HttpUrl] = None
    social_twitter: Optional[HttpUrl] = None
    social_instagram: Optional[HttpUrl] = None
    social_linkedin: Optional[HttpUrl] = None

    #Feature toggles controlling visible sections
    show_enquiry_form: bool = True
    show_testimonials: bool = False
    show_pricing: bool = False

    #Dynamic content lists rendered on the site
    testimonials: List[Testimonial] = Field(default_factory=list)
    pricing_plans: List[PricingPlan] = Field(default_factory=list)

    #UI styling configuration
    border_radius: Literal["none", "small", "medium", "large"] = "medium"
    text_alignment: Literal["left", "center", "right"] = "center"
    button_style: Literal["solid", "outline", "ghost"] = "solid"

    #Ordered list of sections to render on the page
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

    #Global animation enable/disable toggle
    animation_enabled: bool = True

    #Optional custom CSS injected into the public site
    custom_css: Optional[str] = None


#Payload used to partially update customisation settings via PATCH
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


#Full customisation object returned to authenticated businesses
class CustomisationOut(CustomisationBase):
    id: int
    business_id: int
    logo_path: Optional[str] = None

    model_config = {"from_attributes": True}
