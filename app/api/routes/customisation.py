from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

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
