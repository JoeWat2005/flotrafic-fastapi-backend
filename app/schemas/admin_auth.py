from pydantic import BaseModel, EmailStr

"""
ADMIN AUTH SCHEMA
"""


#Payload used by admins to authenticate via the admin login endpoint
class AdminLogin(BaseModel):
    email: EmailStr
    password: str