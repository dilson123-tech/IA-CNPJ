from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.deps import get_db
from app.models.company import Company
from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionOut

router = APIRouter(prefix="/transactions", tags=["transactions"])

@router.post("", response_model=TransactionOut)
def create_transaction(payload: TransactionCreate, db: Session = Depends(get_db)):
    # valida company
    company = db.get(Company, payload.company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Empresa (company_id) nao existe")

    # valida categoria (se veio)
    if payload.category_id is not None:
        cat = db.get(Category, payload.category_id)
        if not cat:
            raise HTTPException(status_code=404, detail="Categoria (category_id) nao existe")

    t = Transaction(
        company_id=payload.company_id,
        category_id=payload.category_id,
        kind=payload.kind,
        amount_cents=payload.amount_cents,
        description=payload.description or "",
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t

@router.get("", response_model=list[TransactionOut])
def list_transactions(company_id: int | None = None, db: Session = Depends(get_db)):
    q = select(Transaction).order_by(Transaction.id.desc())
    if company_id is not None:
        q = q.where(Transaction.company_id == company_id)
    return list(db.scalars(q))
