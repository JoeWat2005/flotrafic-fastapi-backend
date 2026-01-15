from pydantic import BaseModel

"""
ADMIN AUTH SCHEMA
"""


#Payload used by admins to authenticate via the admin login endpoint
class AdminLogin(BaseModel):
    username: str
    password: str