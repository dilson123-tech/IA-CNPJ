from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.core.tenant import get_current_tenant_id
from app.schemas.usage_credit import UsageCreditResponse
from app.services.usage_credit_service import UsageCreditService

router = APIRouter(prefix="/usage-credits", tags=["Usage Credits"])


@router.get("/me", response_model=UsageCreditResponse)
def get_my_usage_credits(
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    service = UsageCreditService(db)
    return service.get_balance(tenant_id)
