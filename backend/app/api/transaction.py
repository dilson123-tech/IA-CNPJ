from datetime import datetime
from typing import Any
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
    include_no_match: bool = Query(False),
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


# -----------------------------
# Data Quality: sugestões de categoria (rule-based)
# -----------------------------

def _normalize_text(s: str) -> str:
    return (s or "").strip().lower()

def _rules() -> list[dict[str, Any]]:
    # Ordem importa: primeira regra que casar vence (confidence pode variar)
    return [
        {"rule": "pix|qr|transfer", "keywords": ["pix", "qr", "transfer"], "category_name": "Vendas", "confidence": 0.70},
        {"rule": "venda|cliente|pedido", "keywords": ["venda", "cliente", "pedido"], "category_name": "Vendas", "confidence": 0.80},
        {"rule": "frete|entrega|transport", "keywords": ["frete", "entrega", "transport"], "category_name": "Fretes", "confidence": 0.75},
        {"rule": "aluguel|locacao", "keywords": ["aluguel", "locacao", "locação"], "category_name": "Aluguel", "confidence": 0.85},
        {"rule": "luz|energia|celesc", "keywords": ["luz", "energia", "celesc"], "category_name": "Energia", "confidence": 0.85},
        {"rule": "agua|água|samae", "keywords": ["agua", "água", "samae"], "category_name": "Água", "confidence": 0.85},
        {"rule": "internet|wifi|provedor", "keywords": ["internet", "wifi", "provedor"], "category_name": "Internet", "confidence": 0.80},
        {"rule": "servidor|server|hosting|vps|cloud|aws|azure|gcp|dominio|dns", "keywords": ["servidor","server","hosting","vps","cloud","aws","azure","gcp","dominio","domínio","dns"], "category_name": "Internet", "confidence": 0.78},
        {"rule": "mercado|super|padaria", "keywords": ["mercado", "super", "padaria"], "category_name": "Compras", "confidence": 0.75},
        {"rule": "combustivel|gasolina|posto", "keywords": ["combustivel", "combustível", "gasolina", "posto"], "category_name": "Combustível", "confidence": 0.80},
        {"rule": "salario|folha|pagamento", "keywords": ["salario", "salário", "folha", "pagamento"], "category_name": "Salários", "confidence": 0.80},
        {"rule": "imposto|taxa|das|simples", "keywords": ["imposto", "taxa", "das", "simples"], "category_name": "Impostos", "confidence": 0.80},
        {"rule": "teste|testes|qa|homolog|homologacao|homologação|experimento", "keywords": ["teste","testes","qa","homolog","homologacao","homologação","experimento"], "category_name": "Testes", "confidence": 0.60},
    ]

# Alias público para testes/contratos (evita ImportError)
RULES = _rules()

def _ensure_categories_by_name(db: Session, company_id: int, names: list[str]) -> dict[str, int]:
    # cria categorias que não existirem, e retorna mapa name->id
    existing = list(db.scalars(select(Category)))
    mp = {c.name: c.id for c in existing}
    changed = False
    for name in names:
        if name not in mp:
            c = Category(name=name)
            db.add(c)
            db.flush()
            mp[name] = c.id
            changed = True
    if changed:
        db.commit()
    return mp

@router.get("/suggest-categories")
def suggest_categories(
    company_id: int = Query(..., ge=1),
    start: str | None = None,
    end: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    include_no_match: bool = Query(False),
    db: Session = Depends(get_db),
):
    """
    Sugere categoria para transações sem categoria (rule-based).
    Retorna lista: {id, suggested_category_id, confidence, rule, description, provider, reason, signals}
    """
    rep._ensure_company(db, company_id)
    start_dt, end_dt, _period = rep._resolve_period(start, end)

    # pega uncategorized bruto (igual ao endpoint /uncategorized)
    q = (
        select(
            Transaction.id,
            Transaction.description,
            Transaction.amount_cents,
            Transaction.kind,
            Transaction.occurred_at,
        )
        .where(Transaction.company_id == company_id)
        .where(Transaction.occurred_at >= start_dt)
        .where(Transaction.occurred_at <= end_dt)
        .where(Transaction.category_id.is_(None))
        .order_by(Transaction.occurred_at.desc(), Transaction.id.desc())
        .limit(limit)
    )
    rows = db.execute(q).all()

    rules = _rules()
    needed_names = sorted({r["category_name"] for r in rules})
    cat_map = _ensure_categories_by_name(db, company_id, needed_names)

    out = []
    for r in rows:
        desc = _normalize_text(r.description or "")
        suggested = None
        matched_kw = None
        for rule in rules:
            for k in rule["keywords"]:
                if k in desc:
                    suggested = rule
                    matched_kw = k
                    break
            if suggested:
                break
        if suggested:
            out.append({
                "id": r.id,
                "suggested_category_id": cat_map.get(suggested["category_name"]),
                "confidence": suggested["confidence"],
                "rule": suggested["rule"],
                "description": r.description or "",
                # D11: auditável
                "provider": "rule-based",
                "reason": (f"keyword match: {matched_kw}" if matched_kw else f"matched rule: {suggested['rule']}"),
                "signals": ([f"rule:{suggested['rule']}"] + ([f"kw:{matched_kw}"] if matched_kw else [])),
            })
        elif include_no_match:
            out.append({
                "id": r.id,
                "suggested_category_id": None,
                "confidence": 0.0,
                "rule": "no_match",
                "description": r.description or "",
                # D11: auditável
                "provider": "rule-based",
                "reason": "no keyword match",
                "signals": ["rule:no_match"],
            })
    # por padrão, NÃO devolve no_match (só sugestões aplicáveis)
    if not include_no_match:
        out = [x for x in out if x.get("suggested_category_id") is not None]
    return out




@router.post("/apply-suggestions")
def apply_suggestions(
    company_id: int = Query(..., ge=1),
    start: str | None = None,
    end: str | None = None,
    limit: int = Query(200, ge=1, le=500),
    dry_run: bool = Query(False),
    db: Session = Depends(get_db),
):
    """
    Aplica sugestões de categoria (rule-based) para transações sem categoria no período.
    - dry_run=true: não altera nada, só retorna o que faria.
    """
    rep._ensure_company(db, company_id)
    start_dt, end_dt, _period = rep._resolve_period(start, end)

    suggestions = suggest_categories(
        company_id=company_id,
        start=start,
        end=end,
        limit=limit,
        db=db,
    )

    suggested_count = sum(1 for s in suggestions if s.get('suggested_category_id'))

    if dry_run:
        return {
            "company_id": company_id,
            "period": {"start": start_dt.date().isoformat(), "end": end_dt.date().isoformat()},
            "dry_run": True,
            "suggested": suggested_count,
            "updated": 0,
            "items": suggestions,
        }

    items = [
        {"id": s["id"], "category_id": s["suggested_category_id"]}
        for s in suggestions
        if s.get("suggested_category_id")
    ]

    if not items:
        return {
            "company_id": company_id,
            "period": {"start": start_dt.date().isoformat(), "end": end_dt.date().isoformat()},
            "dry_run": False,
            "suggested": suggested_count,
            "updated": 0,
            "missing_ids": [],
            "skipped_ids": [],
            "invalid_category_ids": [],
        }

    req = BulkCategorizeRequest(company_id=company_id, items=items)
    res = bulk_categorize(req, db=db)

    # compat pydantic v1/v2
    payload = res.model_dump() if hasattr(res, "model_dump") else dict(res)

    return {
        "company_id": company_id,
        "period": {"start": start_dt.date().isoformat(), "end": end_dt.date().isoformat()},
        "dry_run": False,
        "suggested": suggested_count,
        **payload,
    }

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
