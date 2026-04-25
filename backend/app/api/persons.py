from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.core.tenant import get_current_tenant_id
from app.schemas.person import PersonCreate, PersonResponse
from app.services.person_service import PersonService

router = APIRouter(prefix="/persons", tags=["Persons"])


@router.post("/validate", response_model=PersonResponse)
def validate_person(
    payload: PersonCreate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    service = PersonService(db)
    return service.upsert_person(tenant_id=tenant_id, payload=payload)
