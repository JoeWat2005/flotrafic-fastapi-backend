from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from uuid import uuid4
import os

from app.db.session import get_db
from app.db.models import Business, BusinessCustomisation
from app.api.deps import get_current_business
from app.schemas.customisation import CustomisationOut, CustomisationUpdate
from app.services.audit import log_action

router = APIRouter(
    prefix="/customisation",
    tags=["Website Customisation"],
)

@router.get("/", response_model=CustomisationOut)
def get_customisation(
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    cust = business.customisation
    
    # If it doesn't exist, create default
    if not cust:
        cust = BusinessCustomisation(business_id=business.id)
        db.add(cust)
        db.commit()
        db.refresh(cust)
        
    return cust

@router.patch("/", response_model=CustomisationOut)
def update_customisation(
    payload: CustomisationUpdate,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    cust = business.customisation
    if not cust:
        cust = BusinessCustomisation(business_id=business.id)
        db.add(cust)
    
    update_data = payload.model_dump(exclude_unset=True)

    update_data.pop("logo_path", None)
    update_data.pop("logo_url", None)
    
    for field, value in update_data.items():
        setattr(cust, field, value)
        
    db.commit()
    db.refresh(cust)

    log_action(
        db=db,
        actor_type="business",
        actor_id=business.id,
        action="customisation.updated",
        details="fields=" + ",".join(update_data.keys()),
    )
    
    return cust

@router.post("/logo")
def upload_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    if file.content_type not in ("image/png", "image/jpeg", "image/webp"):
        raise HTTPException(400, "Unsupported image type")

    # Ensure customisation exists
    cust = business.customisation
    if not cust:
        cust = BusinessCustomisation(business_id=business.id)
        db.add(cust)
        db.flush()

    # Delete old logo if exists
    if cust.logo_path:
        old_path = os.path.join("uploads", cust.logo_path)
        if os.path.exists(old_path):
            os.remove(old_path)

    # Generate safe filename
    ext = file.filename.split(".")[-1].lower()
    filename = f"{uuid4()}.{ext}"

    upload_dir = "uploads/logos"
    os.makedirs(upload_dir, exist_ok=True)

    path = os.path.join(upload_dir, filename)

    with open(path, "wb") as f:
        f.write(file.file.read())

    cust.logo_path = f"logos/{filename}"
    db.commit()

    return {"success": True}
