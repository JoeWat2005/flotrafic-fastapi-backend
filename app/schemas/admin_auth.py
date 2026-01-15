from pydantic import BaseModel

"""
ADMIN AUTH SCHEMA
"""

#admin login
class AdminLogin(BaseModel):
    username: str
    password: str
