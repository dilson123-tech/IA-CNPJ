from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.ai import AiConsultRequest, AiConsultResponse
from app.schemas.reports import Period, Totals, CategoryBreakdown, TransactionBrief
from app.api import reports as rep


router = APIRouter(prefix="/ai", tags=["ai"])


def _fmt_brl(cents: int) -> str:
    v = cents / 100.0
    # formatação simples, sem locale
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@router.post("/consult", response_model=AiConsultResponse)
def consult(payload: AiConsultRequest, db: Session = Depends(get_db)):
    # reaproveita helpers do reports (mesma lógica do período)
    start_dt, end_dt, period = rep._resolve_period(payload.start, payload.end)
    totals: Totals = rep._totals_row(db, payload.company_id, start_dt, end_dt)
    by_cat = rep._by_category(db, payload.company_id, start_dt, end_dt)

    # recentes (mesma query do context)
    ctx = rep.context(
        company_id=payload.company_id,
        start=payload.start,
        end=payload.end,
        limit=payload.limit,
        db=db,
    )

    entradas = totals.entradas_cents
    saidas = totals.saidas_cents
    saldo = totals.saldo_cents

    # headline
    if saldo >= 0:
        headline = f"Saldo positivo de {_fmt_brl(saldo)} no período."
    else:
        headline = f"Saldo negativo de {_fmt_brl(abs(saldo))} no período."

    # insights / risks / actions (determinístico)
    insights: list[str] = []
    risks: list[str] = []
    actions: list[str] = []

    if totals.qtd_transacoes == 0:
        insights.append("Sem transações no período — nada para analisar ainda.")
        actions.append("Registre pelo menos entradas e saídas principais para gerar um diagnóstico.")
    else:
        # taxa simples
        if entradas > 0:
            margem = saldo / max(1, entradas)
            insights.append(f"Eficiência do caixa: {margem*100:.1f}% (saldo/entradas).")
        else:
            risks.append("Sem entradas registradas no período — caixa depende só de saldo anterior.")
            actions.append("Garanta o registro de receitas (entradas) com categoria e descrição.")

        # categoria dominante
        if by_cat:
            top = by_cat[0]
            insights.append(f"Categoria com maior volume: {top.category_name} (saldo {_fmt_brl(top.saldo_cents)}).")

        # sem categoria
        semcat = next((c for c in by_cat if c.category_id is None), None)
        if semcat and semcat.qtd_transacoes >= 2:
            risks.append("Muitas transações estão 'Sem categoria' — isso derruba a qualidade da análise.")
            actions.append("Classifique transações antigas e force categoria nas novas (UX/API).")

        # burn
        if saidas > entradas and entradas > 0:
            risks.append("Saídas maiores que entradas no período (burn).")
            actions.append("Investigue custos e defina teto por categoria de despesa.")

        # pergunta do usuário (placeholder)
        if payload.question:
            insights.append(f"Pergunta recebida: {payload.question}")

    # top categories (limita)
    top_categories = by_cat[:8]

    return AiConsultResponse(
        company_id=payload.company_id,
        period=period,
        generated_at=datetime.utcnow(),
        headline=headline,
        insights=insights,
        risks=risks,
        actions=actions,
        numbers=totals,
        top_categories=top_categories,
        recent_transactions=ctx.recent_transactions,  # já vem no formato schema
    )
