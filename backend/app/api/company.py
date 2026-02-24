from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
import logging

from app.deps import get_db
from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyOut
from app.core.tenant import get_current_tenant_id

router = APIRouter(prefix="/companies", tags=["companies"])

logger = logging.getLogger(__name__)


@router.post("", response_model=CompanyOut, status_code=201)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db), tenant_id: int = Depends(get_current_tenant_id)):
    exists = db.scalar(select(Company).where(Company.cnpj == payload.cnpj).where(Company.tenant_id == tenant_id))
    if exists:
        raise HTTPException(status_code=409, detail="CNPJ ja cadastrado")
    c = Company(cnpj=payload.cnpj, razao_social=payload.razao_social, tenant_id=tenant_id)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.get("", response_model=list[CompanyOut])
def list_companies(db: Session = Depends(get_db), tenant_id: int = Depends(get_current_tenant_id)):
    return list(db.scalars(select(Company).where(Company.tenant_id == tenant_id).order_by(Company.id)))


@router.get("/{company_id}", response_model=CompanyOut)
def get_company(company_id: int, db: Session = Depends(get_db), tenant_id: int = Depends(get_current_tenant_id)):
    try:
        c = db.scalar(select(Company).where(Company.id == company_id).where(Company.tenant_id == tenant_id))

        if not c:
            raise HTTPException(status_code=404, detail="Nao encontrado")

        return c

    except HTTPException:
        raise

    except SQLAlchemyError:
        logger.exception("DB error fetching company_id=%s", company_id)
        raise HTTPException(status_code=503, detail="Database unavailable")

    except Exception:
        logger.exception("Unexpected error fetching company_id=%s", company_id)
        raise HTTPException(status_code=500, detail="Internal error")
