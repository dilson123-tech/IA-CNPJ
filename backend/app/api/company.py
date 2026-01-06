from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.deps import get_db
from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyOut

router = APIRouter(prefix="/companies", tags=["companies"])

@router.post("", response_model=CompanyOut)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db)):
    exists = db.scalar(select(Company).where(Company.cnpj == payload.cnpj))
    if exists:
        raise HTTPException(status_code=409, detail="CNPJ ja cadastrado")
    c = Company(cnpj=payload.cnpj, razao_social=payload.razao_social)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c

@router.get("", response_model=list[CompanyOut])
def list_companies(db: Session = Depends(get_db)):
    return list(db.scalars(select(Company).order_by(Company.id)))

@router.get("/{company_id}", response_model=CompanyOut)
def get_company(company_id: int, db: Session = Depends(get_db)):
    c = db.get(Company, company_id)
    if not c:
        raise HTTPException(status_code=404, detail="Nao encontrado")
    return c
