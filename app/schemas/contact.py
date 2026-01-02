from pydantic import BaseModel, EmailStr, Field

class ContactCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    message: str = Field(min_length=10, max_length=2000)

class ContactOut(BaseModel):
    id: int
    name: str
    email: str
    message: str

    class Config:
        from_attributes = True