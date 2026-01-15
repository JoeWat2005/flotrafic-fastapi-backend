from pydantic import BaseModel

"""
ADMIN AUTH SCHEMA
"""

class AdminLogin(BaseModel):
    username: str
    password: str
