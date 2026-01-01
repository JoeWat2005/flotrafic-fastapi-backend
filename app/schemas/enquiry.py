from pydantic import BaseModel
from datetime import datetime

class EnquiryCreate(BaseModel):
    name: str
    email: str
    message: str


class EnquiryOut(BaseModel):
    id: int
    name: str
    email: str
    message: str
    created_at: datetime
    is_read: bool
    status: str

    model_config = {
        "from_attributes": True
    }

