from fastapi import Header, HTTPException
import os

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "dev-admin-key")


def require_admin(x_admin_key: str = Header(...)):
    if x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Admin access required")
