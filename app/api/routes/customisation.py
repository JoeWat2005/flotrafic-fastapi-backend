from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from uuid import uuid4
import os

from app.db.session import get_db
from app.db.models import Business, BusinessCustomisation
from app.api.deps import get_current_business, require_feature
from app.schemas.customisation import CustomisationOut, CustomisationUpdate
from app.services.audit import log_action

router = APIRouter(
    prefix="/customisation",
    tags=["Website Customisation"],
    dependencies=[Depends(require_feature("customisation"))],
)

"""
CUSTOMISATION ROUTES => REQUIRE FEATURE "customisation" AND BUSINESS AUTH
"""


@router.get("/", response_model=CustomisationOut)
def get_customisation(
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    cust = business.customisation

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

    # Prevent logo mutation via PATCH
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
    content_type_to_ext = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/webp": "webp",
    }

    if file.content_type not in content_type_to_ext:
        raise HTTPException(status_code=400, detail="Unsupported image type")

    cust = business.customisation
    if not cust:
        cust = BusinessCustomisation(business_id=business.id)
        db.add(cust)
        db.flush()

    # Delete old logo
    if cust.logo_path:
        old_path = os.path.join("uploads", cust.logo_path)
        if os.path.exists(old_path):
            os.remove(old_path)

    ext = content_type_to_ext[file.content_type]
    filename = f"{uuid4()}.{ext}"

    upload_dir = "uploads/logos"
    os.makedirs(upload_dir, exist_ok=True)

    path = os.path.join(upload_dir, filename)
    with open(path, "wb") as f:
        f.write(file.file.read())

    cust.logo_path = f"logos/{filename}"
    db.commit()

    log_action(
        db=db,
        actor_type="business",
        actor_id=business.id,
        action="customisation.logo_uploaded",
        details=f"filename={filename}",
    )

    return {"success": True}
