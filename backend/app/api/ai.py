from __future__ import annotations

import os
import traceback

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.ai import AISuggestCategoriesRequest, AISuggestCategoriesResponse, AISuggestedItem
from app.schemas.ai import AIApplySuggestionsRequest, AIApplySuggestionsResponse
from app.schemas.ai import AiConsultRequest, AiConsultResponse
from app.schemas.reports import Period, Totals, CategoryBreakdown, TransactionBrief
from app.api import reports as rep
from app.api.transaction import suggest_categories
from app.api.transaction import apply_suggestions as tx_apply_suggestions


router = APIRouter(prefix="/ai", tags=["ai"])


def _fmt_brl(cents: int) -> str:
    v = cents / 100.0
    # formatação simples, sem locale
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@router.post("/consult", response_model=AiConsultResponse)
def consult(payload: AiConsultRequest, db: Session = Depends(get_db)):
    try:
        rep._ensure_company(db, payload.company_id)
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

    except HTTPException:

        raise


    except Exception as e:
        env = os.getenv('ENV', 'lab')

        detail = {

            'error_code': 'AI_CONSULT_FAILED',

            'message': str(e),

            'hint': 'Verifique logs do uvicorn e valide /reports/context para o mesmo período.',

        }

        if env == 'lab':

            detail['trace'] = traceback.format_exc(limit=6)

        raise HTTPException(status_code=500, detail=detail)

@router.post("/suggest-categories", response_model=AISuggestCategoriesResponse)
def ai_suggest_categories(payload: AISuggestCategoriesRequest, db: Session = Depends(get_db)):
    """
    Fase D06: endpoint AI (stub) que reaproveita o rule-based do /transactions/suggest-categories.
    Depois trocamos por LLM sem quebrar contrato.
    """
    items = suggest_categories(
        company_id=payload.company_id,
        start=payload.start,
        end=payload.end,
        limit=payload.limit,
        include_no_match=payload.include_no_match,
        db=db,
    )

    # resposta no contrato do schema AI
    return {
        "company_id": payload.company_id,
        "period": {"start": payload.start, "end": payload.end},
        "items": items,
    }

@router.post("/apply-suggestions", response_model=AIApplySuggestionsResponse)
def ai_apply_suggestions(payload: AIApplySuggestionsRequest, db: Session = Depends(get_db)):
    # Facade IA: reaproveita Data Quality do /transactions.
    # include_no_match só faz sentido no dry_run (debug/triagem), pq no apply não tem o que aplicar em no_match.
    try:
        rep._ensure_company(db, payload.company_id)
        start_dt, end_dt, _period = rep._resolve_period(payload.start, payload.end)

        if payload.dry_run and payload.include_no_match:
            items = suggest_categories(
                company_id=payload.company_id,
                start=payload.start,
                end=payload.end,
                limit=payload.limit,
                include_no_match=True,
                db=db,
            )
            suggested = sum(1 for s in items if s.get("suggested_category_id"))
            data = {
                "company_id": payload.company_id,
                "period": {"start": start_dt.date().isoformat(), "end": end_dt.date().isoformat()},
                "dry_run": True,
                "suggested": suggested,
                "updated": 0,
                "items": items,
                "missing_ids": [],
                "skipped_ids": [],
                "invalid_category_ids": [],
            }
        else:
            # apply real (ou dry_run normal) – NÃO repassa include_no_match
            data = tx_apply_suggestions(
                company_id=payload.company_id,
                start=payload.start,
                end=payload.end,
                limit=payload.limit,
                dry_run=payload.dry_run,
                db=db,
            )
            if isinstance(data, dict):
                data.setdefault("items", [])

        # valida no schema (pydantic v2/v1 compat)
        if hasattr(AIApplySuggestionsResponse, "model_validate"):
            return AIApplySuggestionsResponse.model_validate(data)
        if hasattr(AIApplySuggestionsResponse, "parse_obj"):
            return AIApplySuggestionsResponse.parse_obj(data)
        return AIApplySuggestionsResponse(**data)

    except HTTPException:
        raise
    except Exception as e:
        env = os.getenv("ENV", "lab")
        detail = {
            "error_code": "AI_APPLY_SUGGESTIONS_FAILED",
            "message": str(e),
            "hint": "Veja /tmp/ia-cnpj-uvicorn.log e compare com /transactions/apply-suggestions (mesmo período).",
        }
        if env == "lab":
            detail["trace"] = traceback.format_exc(limit=8)
        raise HTTPException(status_code=500, detail=detail)

