from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.deps import get_db
from app.api import reports as rep
from app.schemas.reports import TransactionBrief
from app.models.company import Company
from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionOut, TransactionCategoryPatch, BulkCategorizeRequest, BulkCategorizeResponse

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
       occurred_at=getattr(payload, "occurred_at", None) or datetime.utcnow(),
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

@router.get("/uncategorized", response_model=list[TransactionBrief])
def uncategorized(
    company_id: int = Query(..., ge=1),
    start: str | None = None,
    end: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Lista transações sem categoria (category_id IS NULL) no período.
    Útil para limpeza de dados (data quality).
    """
    # valida empresa e período (reaproveita do reports)
    rep._ensure_company(db, company_id)
    start_dt, end_dt, _period = rep._resolve_period(start, end)

    q = (
        select(
            Transaction.id,
            Transaction.occurred_at,
            Transaction.kind,
            Transaction.amount_cents,
            Transaction.category_id,
            Transaction.description,
        )
        .where(Transaction.company_id == company_id)
        .where(Transaction.occurred_at >= start_dt)
        .where(Transaction.occurred_at <= end_dt)
        .where(Transaction.category_id.is_(None))
        .order_by(Transaction.occurred_at.desc(), Transaction.id.desc())
        .offset(offset)
        .limit(limit)
    )

    rows = db.execute(q).all()
    out: list[TransactionBrief] = []
    for r in rows:
        out.append(
            TransactionBrief(
                id=r.id,
                occurred_at=r.occurred_at.isoformat(),
                kind=r.kind,
                amount_cents=r.amount_cents,
                category_id=None,
                category_name="Sem categoria",
                description=r.description,
            )
        )
    return out


@router.patch("/{tx_id}/category", response_model=TransactionOut)
def set_transaction_category(
    tx_id: int,
    payload: TransactionCategoryPatch,
    company_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
):
    rep._ensure_company(db, company_id)

    tx = db.get(Transaction, tx_id)
    if not tx or tx.company_id != company_id:
        raise HTTPException(status_code=404, detail="Transacao nao existe para essa empresa")

    if payload.category_id is not None:
        cat = db.get(Category, payload.category_id)
        if not cat:
            raise HTTPException(status_code=404, detail="Categoria (category_id) nao existe")
        if hasattr(cat, "company_id") and getattr(cat, "company_id") != company_id:
            raise HTTPException(status_code=422, detail={
                "error_code": "CATEGORY_OTHER_COMPANY",
                "message": "Categoria nao pertence a esta empresa",
                "category_id": payload.category_id,
            })

    tx.category_id = payload.category_id
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


@router.post("/bulk-categorize", response_model=BulkCategorizeResponse)
def bulk_categorize(payload: BulkCategorizeRequest, db: Session = Depends(get_db)):
    rep._ensure_company(db, payload.company_id)

    items = payload.items or []
    if not items:
        return BulkCategorizeResponse(company_id=payload.company_id, updated=0)

    if len(items) > 500:
        raise HTTPException(status_code=422, detail={
            "error_code": "TOO_MANY_ITEMS",
            "message": "Limite de 500 itens por lote",
            "value": len(items),
        })

    tx_ids = [it.id for it in items]
    tx_rows = list(db.scalars(select(Transaction).where(Transaction.id.in_(tx_ids))))
    tx_by_id = {t.id: t for t in tx_rows}

    cat_ids = sorted({it.category_id for it in items if it.category_id is not None})
    existing_cat_ids: set[int] = set()
    if cat_ids:
        q = select(Category.id).where(Category.id.in_(cat_ids))
        if hasattr(Category, "company_id"):
            q = q.where(Category.company_id == payload.company_id)
        existing_cat_ids = set(db.scalars(q).all())

    invalid_cat_ids = sorted(set(cat_ids) - existing_cat_ids)

    updated = 0
    missing: list[int] = []
    skipped: list[int] = []

    for it in items:
        tx = tx_by_id.get(it.id)
        if not tx:
            missing.append(it.id)
            continue
        if tx.company_id != payload.company_id:
            skipped.append(it.id)
            continue
        if it.category_id is not None and it.category_id in invalid_cat_ids:
            continue
        tx.category_id = it.category_id
        updated += 1

    db.commit()

    return BulkCategorizeResponse(
        company_id=payload.company_id,
        updated=updated,
        missing_ids=sorted(set(missing)),
        skipped_ids=sorted(set(skipped)),
        invalid_category_ids=invalid_cat_ids,
    )
