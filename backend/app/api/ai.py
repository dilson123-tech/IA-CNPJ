from __future__ import annotations

from app.ai.provider import provider_suggest_categories
import os
import traceback
import logging
from uuid import uuid4
from time import perf_counter

from datetime import datetime, timedelta
import re
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import select, func, case

from app.db import get_db
from app.schemas.ai import AISuggestCategoriesRequest, AISuggestCategoriesResponse
from app.schemas.ai import AIApplySuggestionsRequest, AIApplySuggestionsResponse
from app.schemas.ai import AiConsultRequest, AiConsultResponse
from app.schemas.reports import Totals
from app.api import reports as rep
from app.api.transaction import suggest_categories
from app.api.transaction import apply_suggestions as tx_apply_suggestions

from app.models.transaction import Transaction


from app.core.tenant import get_current_tenant_id
router = APIRouter(prefix="/ai", tags=["ai"])

logger = logging.getLogger(__name__)


def _fmt_brl(cents: int) -> str:
    v = cents / 100.0
    # formatação simples, sem locale
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@router.post("/consult", response_model=AiConsultResponse)
def consult(payload: AiConsultRequest, request: Request, db: Session = Depends(get_db), tenant_id: int = Depends(rep.get_current_tenant_id)):
    request_id = request.headers.get('x-request-id') or uuid4().hex
    t0 = perf_counter()
    try:
        tenant_id = get_current_tenant_id()
        rep._ensure_company(db, payload.company_id, get_current_tenant_id())
        # reaproveita helpers do reports (mesma lógica do período)
        start_dt, end_dt, period = rep._resolve_period(payload.start, payload.end)
        totals: Totals = rep._totals_row(db, payload.company_id, start_dt, end_dt, tenant_id)
        by_cat = rep._by_category(db, payload.company_id, start_dt, end_dt, tenant_id)
        # sem categoria (derivado de by_cat) — usado no score
        semcat = next((c for c in by_cat if getattr(c, 'category_id', None) is None), None)


        # recentes (mesma query do context)

        # -----------------------------
        # Motor v1: diagnóstico mais forte (sem mudar o schema)
        # - top saídas por categoria (percentual)
        # - top despesas por descrição (onde está sangrando)
        # - recorrência (assinaturas / repetidas)
        # - comparação com período anterior (mesma duração)
        # -----------------------------
        def _norm_desc(s: str) -> str:
            s = (s or "").strip().lower()
            s = re.sub(r"\s+", " ", s)
            s = s.replace("-", " ").replace("_", " ")
            s = re.sub(r"\s+", " ", s).strip()
            return s[:60] if len(s) > 60 else s

        # comparação com período anterior (mesmo número de dias)
        try:
            days = (end_dt.date() - start_dt.date()).days + 1
            prev_end = start_dt.date() - timedelta(days=1)
            prev_start = prev_end - timedelta(days=days - 1)

            prev_start_dt = datetime(prev_start.year, prev_start.month, prev_start.day, 0, 0, 0)
            prev_end_dt = datetime(prev_end.year, prev_end.month, prev_end.day, 23, 59, 59, 999999)

            totals_prev: Totals = rep._totals_row(db, payload.company_id, prev_start_dt, prev_end_dt, tenant_id)
            prev_saidas = int(getattr(totals_prev, "saidas_cents", 0) or 0)
            prev_entradas = int(getattr(totals_prev, "entradas_cents", 0) or 0)
        except Exception:
            totals_prev = None
            prev_saidas = 0
            prev_entradas = 0

        # recentes (igual ao reports.context, mas sem chamar endpoint)
        q_recent = (
            select(
                Transaction.id,
                Transaction.occurred_at,
                Transaction.kind,
                Transaction.amount_cents,
                Transaction.category_id,
                Transaction.description,
            )
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
                "description": r.description or "",
            }
            for r in db.execute(q_recent).all()
        ]

        # top saídas por categoria (percentual)
        by_out = sorted(by_cat or [], key=lambda c: int(getattr(c, "saidas_cents", 0) or 0), reverse=True)
        top_out_cats = [c for c in by_out if int(getattr(c, "saidas_cents", 0) or 0) > 0][:3]

        # top despesas por descrição (PERÍODO INTEIRO, só "out")
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
            top_desc.append({'sample': sample[:80], 'sum': int(getattr(r, 'sum_cents', 0) or 0), 'cnt': int(getattr(r, 'cnt', 0) or 0)})

        # recorrência: mesma descrição >=2 e soma >= R$10,00 (1000 cents)
        q_rec = (
            select(
                desc_key.label('k'),
                func.sum(Transaction.amount_cents).label('sum_cents'),
                func.count(Transaction.id).label('cnt'),
                func.max(desc_raw).label('sample'),
            )
            .where(
                Transaction.company_id == payload.company_id,
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

        # maior gasto único no período (pico)
        q_single = (
            select(desc_raw.label('description'), Transaction.amount_cents.label('amount_cents'))
            .where(
                Transaction.company_id == payload.company_id,
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

        entradas = totals.entradas_cents
        saidas = totals.saidas_cents
        saldo = totals.saldo_cents
                # -----------------------------
        # Runway Engine v1 (determinístico)
        # - evita float drift: tudo em cents/dias inteiros
        # - runway_days_int pode ser negativo (déficit estrutural)
        # -----------------------------
        days = (end_dt.date() - start_dt.date()).days + 1
        days = max(1, int(days))

        # média diária de saídas em cents/dia (inteiro, arredondando pra cima)
        avg_daily_out_cents = (saidas + (days - 1)) // days if saidas > 0 else 0

        runway_days_int = None
        runway_status = None

        if avg_daily_out_cents > 0:
            runway_days_int = saldo // avg_daily_out_cents  # pode ser negativo

            if runway_days_int < 0:
                runway_status = "déficit estrutural"
            elif runway_days_int < 15:
                runway_status = "crítico"
            elif runway_days_int < 30:
                runway_status = "alto risco"
            elif runway_days_int < 60:
                runway_status = "atenção"
            else:
                runway_status = "saudável"

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



            # top saídas por categoria (com percentual)

            if saidas > 0 and top_out_cats:

                parts = []

                for c in top_out_cats:

                    oc = int(getattr(c, "saidas_cents", 0) or 0)

                    pct = round((oc / saidas) * 100.0, 1) if saidas > 0 else 0.0

                    parts.append(f"{getattr(c, 'category_name', '?')} {pct:.1f}%")

                insights.append("Principais saídas por categoria: " + " | ".join(parts) + ".")


                # risco: concentração alta numa categoria

                c0 = top_out_cats[0]

                c0_out = int(getattr(c0, "saidas_cents", 0) or 0)

                c0_pct = (c0_out / saidas) * 100.0 if saidas > 0 else 0.0

                if c0_pct >= 45.0:

                    risks.append(f"Alta concentração de despesas em {getattr(c0, 'category_name', '?')} (~{c0_pct:.0f}% das saídas).")

                    actions.append("Quebre essa categoria em subcategorias e defina teto (limite) semanal/mensal.")


            # onde está gastando mais (por descrição, do contexto recente)

            if top_desc:

                for i, v in enumerate(top_desc[:3], start=1):
                    soma = int(v["sum"])
                    cnt = int(v["cnt"])
                    pct_saidas = (soma / saidas * 100.0) if saidas > 0 else 0.0
                    pct_entradas = (soma / entradas * 100.0) if entradas > 0 else 0.0

                    insights.append(
                        f"Top gasto #{i}: {v['sample']} — {_fmt_brl(soma)} "
                        f"({cnt}x | {pct_saidas:.1f}% das saídas"
                        + (f" | {pct_entradas:.1f}% das entradas" if entradas > 0 else "")
                        + ")."
                    )

                    if pct_saidas >= 40.0:
                        risks.append(
                            f"Alta dependência de um único fornecedor/descrição "
                            f"({pct_saidas:.0f}% das saídas)."
                        )
                        actions.append(
                            "Avalie renegociação, troca de fornecedor ou limite mensal específico."
                        )


            # recorrência (assinaturas / cobranças repetidas)

            if recurring:

                risks.append("Detectei despesas recorrentes (mesma descrição repetida) — possível assinatura/cobrança automática.")

                for v in recurring[:2]:

                    actions.append(f"Revise: {v['sample']} — {_fmt_brl(int(v['sum']))} em {int(v['cnt'])} ocorrências.")


            # pico (maior gasto único)
            if int(top_single_amt or 0) > 0:
                pct = (int(top_single_amt) / saidas) * 100.0 if saidas > 0 else 0.0
                if int(top_single_amt) >= 50000 or pct >= 25.0:
                    risks.append(f"Gasto alto único: {(top_single_desc or '(sem descrição)')[:70]} — {_fmt_brl(int(top_single_amt))}.")
                    actions.append("Valide esse gasto (nota/recibo). Se for recorrente, renegocie ou troque fornecedor.")
            # comparação com período anterior

            if totals_prev is not None and (prev_saidas > 0 or prev_entradas > 0):

                if prev_saidas > 0:

                    delta = ((saidas - prev_saidas) / prev_saidas) * 100.0

                    insights.append(f"Comparativo: saídas {delta:+.1f}% vs período anterior (mesma duração).")

                    if delta >= 20.0:

                        risks.append("Saídas aumentaram forte vs período anterior — possível descontrole ou despesa extraordinária.")

                        actions.append("Compare transações do topo (descrição) entre os dois períodos e identifique o motivo do salto.")

            # sem categoria
            semcat = next((c for c in by_cat if c.category_id is None), None)
            if semcat and semcat.qtd_transacoes >= 2:
                risks.append("Muitas transações estão 'Sem categoria' — isso derruba a qualidade da análise.")
                actions.append("Classifique transações antigas e force categoria nas novas (UX/API).")

            # burn
            if saidas > entradas and entradas > 0:
                risks.append("Saídas maiores que entradas no período (burn).")
                actions.append("Investigue custos e defina teto por categoria de despesa.")

            
                # insight runway
                if runway_days_int is not None:
                    if runway_days_int < 0:
                        insights.append("Empresa opera em déficit estrutural no ritmo atual.")
                    else:
                        insights.append(f"Runway estimado: {int(runway_days_int)} dias no ritmo atual de saídas.")
                        if runway_days_int < 29:
                            risks.append("Runway inferior a 30 dias — risco operacional elevado.")
                            actions.append("Reduza despesas imediatamente ou aumente receitas para estender o caixa.")

              # pergunta do usuário (placeholder)
            if payload.question:
                insights.append(f"Pergunta recebida: {payload.question}")


        # -----------------------------

        # Motor v2: Health Score (0-100) + Status (sem mudar schema)

        # Regras determinísticas e auditáveis:

        # - penaliza burn, saldo negativo, sem entradas, sem categoria, concentração, recorrência, picos e aumento vs período anterior

        # -----------------------------

        def _clamp(n: int, lo: int = 0, hi: int = 100) -> int:

            return lo if n < lo else hi if n > hi else n

        

        score = 100

        

        # Base: saldo e atividade

        if saidas > 0 and entradas == 0:

            score -= 25  # gastando sem registrar receita

        if saldo < 0:

            score -= 10

        

        # Burn

        if entradas > 0 and saidas > entradas:

            score -= 15

        

        # sem categoria (derivado de by_cat) — precisa existir antes do score
        semcat = next((c for c in by_cat if getattr(c, 'category_id', None) is None), None)

        # Sem categoria (qualidade do dado)

        if semcat and int(getattr(semcat, "qtd_transacoes", 0) or 0) >= 2:

            score -= 10

        

        # Concentração por categoria (já calculada no v1)

        try:

            if "top_out_cats" in locals() and saidas > 0 and top_out_cats:

                c0 = top_out_cats[0]

                c0_out = int(getattr(c0, "saidas_cents", 0) or 0)

                c0_pct = (c0_out / saidas) * 100.0 if saidas > 0 else 0.0

                if c0_pct >= 45.0:

                    score -= 10

        except Exception:

            pass

        

        # Recorrência / picos

        if "recurring" in locals() and recurring:

            score -= 5

        top_single = locals().get("top_single")

        if top_single is not None:
            top_amt = int(getattr(top_single, "amount_cents", 0) or 0)

            pct = (top_amt / saidas) * 100.0 if saidas > 0 else 0.0

            if top_amt >= 50000 or pct >= 25.0:

                score -= 5

        

        # Comparativo vs período anterior (se disponível)

        try:

            if totals_prev is not None and prev_saidas > 0:

                delta = ((saidas - prev_saidas) / prev_saidas) * 100.0

                if delta >= 20.0:

                    score -= 10

        except Exception:

            pass

        

        score = _clamp(int(score))

        status = "SAUDÁVEL" if score >= 80 else "ATENÇÃO" if score >= 60 else "CRÍTICO"

        insights.insert(0, f"Saúde financeira (score {score}/100): {status}.")

        

        if status == "CRÍTICO":

            actions.insert(0, "Ação imediata: reduza saídas, categorize tudo e registre entradas; revise top gastos e recorrências.")

        elif status == "ATENÇÃO":

            actions.insert(0, "Ajuste recomendado: defina teto por categoria e revise recorrências/picos; melhore qualidade das categorias.")


        # top categories (limita)
        top_categories = by_cat[:8]

        # Motor v2: garante score/status como primeiro insight (sem mudar schema)
        try:
            idx = next(i for i, s in enumerate(insights) if str(s).lower().startswith("saúde financeira"))
            if idx != 0:
                insights.insert(0, insights.pop(idx))
        except StopIteration:
            pass
        # observabilidade mínima (sem dados sensíveis)
        # semcat já calculado acima (mantido determinístico)


        try:


            top_out = max(by_cat, key=lambda c: int(getattr(c, 'saidas_cents', 0) or 0)) if by_cat else None


            top_out_cents = int(getattr(top_out, 'saidas_cents', 0) or 0) if top_out else 0


            top_out_pct = round((top_out_cents / saidas) * 100.0, 1) if saidas > 0 else 0.0


        except Exception:


            top_out_pct = 0.0


        # resumo de categorias para observabilidade (sem dados sensíveis)
        top_cat_summary = []
        for c in top_categories:
            name = getattr(c, 'category_name', None) or getattr(c, 'name', '?')
            qtd = getattr(c, 'qtd_transacoes', None)
            top_cat_summary.append(f"{name}:{qtd}")
        top_cat_summary_str = ",".join(top_cat_summary[:5])

        duration_ms = int((perf_counter() - t0) * 1000)


        logger.info(


            "ai_consult ok request_id=%s company_id=%s start=%s end=%s duration_ms=%s qtd_tx=%s qtd_sem_categoria=%s top_out_pct=%s top_cat=%s",


            request_id, payload.company_id, payload.start, payload.end, duration_ms,


            getattr(totals, 'qtd_transacoes', None),


            getattr(semcat, 'qtd_transacoes', 0) if semcat else 0,


            top_out_pct,
              top_cat_summary_str,


        )


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
            recent_transactions=recent_transactions[:20],  # já vem no formato schema
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
        rep._ensure_company(db, payload.company_id, get_current_tenant_id())
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

