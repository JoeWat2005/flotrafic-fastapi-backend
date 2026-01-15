from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Literal
from datetime import datetime

"""
PUBLIC ROUTE SCHEMA
"""


#Standard success response returned by public write endpoints
class PublicSuccessOut(BaseModel):
    success: bool = True


#Customer testimonial displayed on the public website
class PublicTestimonial(BaseModel):
    name: str
    role: Optional[str] = None
    content: str
    rating: int = Field(default=5, ge=1, le=5)


#Pricing plan displayed on the public website
class PublicPricingPlan(BaseModel):
    name: str
    price: str
    features: List[str] = Field(default_factory=list)
    is_popular: bool = False


#Public-facing customisation settings used to render a business website
class PublicCustomisationOut(BaseModel):
    primary_color: str
    secondary_color: str
    accent_color: str
    logo_url: Optional[str] = None
    font_family: str

    hero_title: str
    hero_subtitle: str
    cta_text: str

    about_title: Optional[str] = None
    about_content: Optional[str] = None

    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_address: Optional[str] = None

    social_facebook: Optional[str] = None
    social_twitter: Optional[str] = None
    social_instagram: Optional[str] = None
    social_linkedin: Optional[str] = None

    show_enquiry_form: bool
    show_pricing: bool
    show_testimonials: bool

    testimonials: List[PublicTestimonial]
    pricing_plans: List[PublicPricingPlan]

    border_radius: Literal["none", "small", "medium", "large"]
    text_alignment: Literal["left", "center", "right"]
    button_style: Literal["solid", "outline", "ghost"]

    section_order: List[str]
    animation_enabled: bool


#Public representation of a business used to render the website
class PublicBusinessOut(BaseModel):
    id: int
    name: str
    slug: str
    customisation: PublicCustomisationOut


#Payload used when a customer submits a public enquiry
class PublicEnquiryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    message: str = Field(min_length=1, max_length=2000)


#Payload used to record anonymous website visit analytics
class PublicVisitCreate(BaseModel):
    slug: str
    path: Optional[str] = "/"
    user_agent: Optional[str] = None


#Payload used when a customer requests a booking time slot
class PublicBookingCreate(BaseModel):
    start_time: datetime
    end_time: datetime
    customer_email: EmailStr