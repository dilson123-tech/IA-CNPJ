from __future__ import annotations

from app.ai.provider import provider_suggest_categories
import os
import traceback

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.ai import AISuggestCategoriesRequest, AISuggestCategoriesResponse
from app.schemas.ai import AIApplySuggestionsRequest, AIApplySuggestionsResponse
from app.schemas.ai import AiConsultRequest, AiConsultResponse
from app.schemas.reports import Totals
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
            recent_transactions=ctx.recent_transactions[:20],  # já vem no formato schema
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
    Facade AI: contrato estável + fallback determinístico.
    Compat: aceita start/end OU start_date/end_date.
    Sempre retorna: {company_id, period:{start,end}, items:[...]}.
    """
    start = getattr(payload, "start", None) or getattr(payload, "start_date", None)
    end = getattr(payload, "end", None) or getattr(payload, "end_date", None)
    if not start or not end:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "INVALID_PERIOD",
                "message": "Informe start/end ou start_date/end_date (ISO yyyy-mm-dd).",
            },
        )

    include_no_match = bool(getattr(payload, "include_no_match", False))
    limit = getattr(payload, "limit", 200)

    # tenta normalizar pro provider (caso ele leia payload.start/payload.end)
    try:
        setattr(payload, "start", start)
        setattr(payload, "end", end)
    except Exception:
        pass

    _ai_res = None
    try:
        _ai_res = provider_suggest_categories(payload, include_no_match=include_no_match)
    except Exception:
        _ai_res = None

    if _ai_res is not None:
        # normaliza qualquer retorno do provider pra dict no schema
        if hasattr(_ai_res, "model_dump"):
            data = _ai_res.model_dump()
        elif hasattr(_ai_res, "dict"):
            data = _ai_res.dict()
        elif isinstance(_ai_res, list):
            data = {"items": _ai_res}
        elif isinstance(_ai_res, dict):
            data = _ai_res
        else:
            data = {}

        data.setdefault("company_id", payload.company_id)

        per = data.get("period") or {}
        if not isinstance(per, dict):
            per = {}
        per["start"] = per.get("start") or start
        per["end"] = per.get("end") or end
        data["period"] = per

        data.setdefault("items", [])

        # D11: normaliza itens do provider para o contrato enterprise (auditável)
        try:
            from app.ai.provider import get_provider_config
            _enabled, _prov_name = get_provider_config()
        except Exception:
            _enabled, _prov_name = True, "ai"
        _prov_name = (str(_prov_name or "ai") or "ai").strip()

        _items = data.get("items") or []
        _norm = []
        for it in _items:
            if hasattr(it, "model_dump"):
                it = it.model_dump()
            elif hasattr(it, "dict"):
                it = it.dict()
            if not isinstance(it, dict):
                continue

            # compat: provider pode vir com transaction_id em vez de id
            if "id" not in it and "transaction_id" in it:
                it["id"] = it.get("transaction_id")

            # defaults D11 (não quebram nada)
            it.setdefault("provider", _prov_name if _enabled else "rule-based")
            it.setdefault("reason", "")
            sig = it.get("signals")
            if sig is None:
                it["signals"] = []
            elif not isinstance(sig, list):
                it["signals"] = [str(sig)]

            # compat com schema antigo
            it.setdefault("rule", "ai")
            it.setdefault("description", "")
            it.setdefault("confidence", 0.0)
            it.setdefault("suggested_category_id", None)

            _norm.append(it)

        data["items"] = _norm
        return data
    # fallback determinístico
    items = suggest_categories(
        company_id=payload.company_id,
        start=start,
        end=end,
        limit=limit,
        include_no_match=include_no_match,
        db=db,
    )

    return {
        "company_id": payload.company_id,
        "period": {"start": start, "end": end},
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

