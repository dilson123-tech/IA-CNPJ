from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api import reports as rep
from app.models.transaction import Transaction
from app.models.category import Category


def run_ai_consult(
    *,
    db: Session,
    payload: Any,
    tenant_id: int,
) -> dict:
    rep._ensure_company(db, payload.company_id, tenant_id)

    start_dt, end_dt, period = rep._resolve_period(payload.start, payload.end)
    totals = rep._totals_row(db, payload.company_id, start_dt, end_dt, tenant_id)
    by_cat = rep._by_category(db, payload.company_id, start_dt, end_dt, tenant_id)
    semcat = next((c for c in by_cat if getattr(c, 'category_id', None) is None), None)

    try:
        days_prev = (end_dt.date() - start_dt.date()).days + 1
        prev_end = start_dt.date() - timedelta(days=1)
        prev_start = prev_end - timedelta(days=days_prev - 1)

        prev_start_dt = datetime(prev_start.year, prev_start.month, prev_start.day, 0, 0, 0)
        prev_end_dt = datetime(prev_end.year, prev_end.month, prev_end.day, 23, 59, 59, 999999)

        totals_prev = rep._totals_row(db, payload.company_id, prev_start_dt, prev_end_dt, tenant_id)
        prev_saidas = int(getattr(totals_prev, "saidas_cents", 0) or 0)
        prev_entradas = int(getattr(totals_prev, "entradas_cents", 0) or 0)
    except Exception:
        prev_saidas = 0
        prev_entradas = 0

    q_recent = (
        select(
            Transaction.id,
            Transaction.occurred_at,
            Transaction.kind,
            Transaction.amount_cents,
            Transaction.category_id,
            func.coalesce(Category.name, "Sem categoria").label("category_name"),
            Transaction.description,
        )
        .select_from(Transaction)
        .outerjoin(Category, Category.id == Transaction.category_id)
        .where(
            Transaction.company_id == payload.company_id,
            Transaction.tenant_id == tenant_id,
            Transaction.occurred_at.is_not(None),
            Transaction.occurred_at >= start_dt,
            Transaction.occurred_at <= end_dt,
        )
        .order_by(Transaction.occurred_at.desc())
        .limit(payload.limit)
    )

    recent_transactions = [
        {
            "id": r.id,
            "occurred_at": r.occurred_at,
            "kind": r.kind,
            "amount_cents": int(r.amount_cents),
            "category_id": r.category_id,
            "category_name": str(r.category_name),
            "description": r.description or "",
        }
        for r in db.execute(q_recent).all()
    ]

    by_out = sorted(by_cat or [], key=lambda c: int(getattr(c, "saidas_cents", 0) or 0), reverse=True)
    top_out_cats = [c for c in by_out if int(getattr(c, "saidas_cents", 0) or 0) > 0][:3]

    desc_raw = func.coalesce(Transaction.description, "")
    desc_key = func.lower(func.trim(desc_raw))
    desc_key = case((desc_key == "", "(sem descrição)"), else_=desc_key)

    q_desc = (
        select(
            desc_key.label('k'),
            func.sum(Transaction.amount_cents).label('sum_cents'),
            func.count(Transaction.id).label('cnt'),
            func.max(desc_raw).label('sample'),
        )
        .where(
            Transaction.company_id == payload.company_id,
            Transaction.tenant_id == tenant_id,
            Transaction.occurred_at.is_not(None),
            Transaction.occurred_at >= start_dt,
            Transaction.occurred_at <= end_dt,
            Transaction.kind == 'out',
        )
        .group_by(desc_key)
        .order_by(func.sum(Transaction.amount_cents).desc(), desc_key.asc())
        .limit(5)
    )

    rows_desc = db.execute(q_desc).all()
    top_desc = []
    for r in rows_desc:
        sample = (getattr(r, 'sample', '') or getattr(r, 'k', '') or '(sem descrição)').strip()
        top_desc.append({
            'sample': sample[:80],
            'sum': int(getattr(r, 'sum_cents', 0) or 0),
            'cnt': int(getattr(r, 'cnt', 0) or 0),
        })

    q_rec = (
        select(
            desc_key.label('k'),
            func.sum(Transaction.amount_cents).label('sum_cents'),
            func.count(Transaction.id).label('cnt'),
            func.max(desc_raw).label('sample'),
        )
        .where(
            Transaction.company_id == payload.company_id,
            Transaction.tenant_id == tenant_id,
            Transaction.occurred_at.is_not(None),
            Transaction.occurred_at >= start_dt,
            Transaction.occurred_at <= end_dt,
            Transaction.kind == 'out',
        )
        .group_by(desc_key)
        .having(func.count(Transaction.id) >= 2)
        .order_by(func.sum(Transaction.amount_cents).desc(), desc_key.asc())
        .limit(3)
    )

    rows_rec = db.execute(q_rec).all()
    recurring = []
    for r in rows_rec:
        s = (getattr(r, 'sample', '') or getattr(r, 'k', '') or '(sem descrição)').strip()
        s_sum = int(getattr(r, 'sum_cents', 0) or 0)
        s_cnt = int(getattr(r, 'cnt', 0) or 0)
        if s_cnt >= 2 and s_sum >= 1000:
            recurring.append({'sample': s[:80], 'sum': s_sum, 'cnt': s_cnt})

    q_single = (
        select(desc_raw.label('description'), Transaction.amount_cents.label('amount_cents'))
        .where(
            Transaction.company_id == payload.company_id,
            Transaction.tenant_id == tenant_id,
            Transaction.occurred_at.is_not(None),
            Transaction.occurred_at >= start_dt,
            Transaction.occurred_at <= end_dt,
            Transaction.kind == 'out',
        )
        .order_by(Transaction.amount_cents.desc())
        .limit(1)
    )

    r_single = db.execute(q_single).first()
    top_single_desc = None
    top_single_amt = 0
    if r_single:
        top_single_desc = (getattr(r_single, 'description', '') or '(sem descrição)').strip()
        top_single_amt = int(getattr(r_single, 'amount_cents', 0) or 0)

    entradas = int(getattr(totals, "entradas_cents", 0) or 0)
    saidas = int(getattr(totals, "saidas_cents", 0) or 0)
    saldo = int(getattr(totals, "saldo_cents", 0) or 0)

    days = max(1, (end_dt.date() - start_dt.date()).days + 1)
    avg_daily_out_cents = (saidas + (days - 1)) // days if saidas > 0 else 0

    insights = []
    risks = []
    actions = []

    if saidas > entradas:
        risks.append("As saídas estão maiores que as entradas no período.")
        actions.append("Reduzir despesas variáveis e rever custos recorrentes imediatamente.")

    if semcat and int(getattr(semcat, "total_cents", 0) or 0) > 0:
        risks.append("Há movimentações sem categoria, reduzindo a precisão da análise.")
        actions.append("Classificar transações sem categoria para melhorar diagnóstico e previsibilidade.")

    if top_desc:
        insights.append(f"Maior concentração de gastos por descrição: {top_desc[0]['sample']}.")

    if recurring:
        insights.append("Foram identificadas despesas recorrentes no período.")
        actions.append("Revisar assinaturas, contratos e cobranças repetidas.")

    if prev_saidas and saidas > prev_saidas:
        risks.append("As saídas cresceram em relação ao período anterior equivalente.")

    if avg_daily_out_cents > 0:
        insights.append(f"Média diária de saídas no período: {avg_daily_out_cents} cents.")

    headline = "Operação financeiramente estável no período."
    if saidas > entradas:
        headline = "As despesas superaram as entradas no período analisado."
    elif saldo > 0 and saidas > 0:
        headline = "A operação fechou o período com saldo positivo."
    elif entradas == 0 and saidas > 0:
        headline = "Foram registradas apenas saídas no período analisado."

    top_categories = [
        {
            "category_id": getattr(c, "category_id", None),
            "category_name": getattr(c, "category_name", "Sem categoria"),
            "entradas_cents": int(getattr(c, "entradas_cents", 0) or 0),
            "saidas_cents": int(getattr(c, "saidas_cents", 0) or 0),
            "saldo_cents": int(getattr(c, "saldo_cents", 0) or 0),
            "qtd_transacoes": int(getattr(c, "qtd_transacoes", 0) or 0),
        }
        for c in top_out_cats
    ]

    recent_transactions_out = [
        {
            "id": int(tx["id"]),
            "occurred_at": tx["occurred_at"],
            "kind": tx["kind"],
            "amount_cents": int(tx["amount_cents"]),
            "category_id": tx["category_id"],
            "category_name": tx["category_name"],
            "description": tx["description"],
        }
        for tx in recent_transactions
    ]

    return {
        "company_id": payload.company_id,
        "period": period,
        "generated_at": datetime.now(timezone.utc),
        "headline": headline,
        "insights": insights,
        "risks": risks,
        "actions": actions,
        "numbers": {
            "entradas_cents": entradas,
            "saidas_cents": saidas,
            "saldo_cents": saldo,
            "qtd_transacoes": len(recent_transactions),
        },
        "top_categories": top_categories,
        "recent_transactions": recent_transactions_out,
    }
