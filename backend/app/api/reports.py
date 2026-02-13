from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from fastapi import Body, Request, Response
import httpx
from io import BytesIO
import json
import os
import datetime as _dt

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from sqlalchemy.orm import Session
from sqlalchemy import func, case, select

from app.db import get_db
from app.models.transaction import Transaction
from app.models.company import Company
from app.models.category import Category
from app.schemas.reports import CategoryBreakdown, ContextResponse, DailyResponse, Period, SummaryResponse, TopCategoriesResponse, Totals, TransactionBrief, DailyPoint

router = APIRouter(prefix="/reports", tags=["reports"])


def _parse_iso_date_or_datetime(s: str, *, is_end: bool) -> datetime:
    """Aceita ISO date (YYYY-MM-DD) ou ISO datetime (YYYY-MM-DDTHH:MM:SS[.fff][Z|±HH:MM]).
    Para date-only:
      - start => 00:00:00
      - end   => 23:59:59.999999
    """
    raw = (s or "").strip()
    if not raw:
        raise HTTPException(
            status_code=422,
            detail={"error_code": "INVALID_DATE", "message": "Data vazia", "value": s},
        )

    s2 = raw.replace(" ", "T")
    if s2.endswith("Z"):
        s2 = s2[:-1] + "+00:00"

    # tenta datetime
    if "T" in s2:
        try:
            dt = datetime.fromisoformat(s2)
            # normaliza tz-aware pra naive (backend usa naive)
            return dt.replace(tzinfo=None) if getattr(dt, "tzinfo", None) else dt
        except Exception:
            pass

    # tenta date-only (pega os 10 primeiros chars pra aceitar "YYYY-MM-DD..." também)
    try:
        from datetime import date as _date
        d = _date.fromisoformat(s2[:10])
    except Exception:
        field = "end" if is_end else "start"
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "INVALID_DATE",
                "field": field,
                "value": raw,
                "expected": ["YYYY-MM-DD", "YYYY-MM-DDTHH:MM:SS"],
            },
        )

    if is_end:
        return datetime(d.year, d.month, d.day, 23, 59, 59, 999999)
    return datetime(d.year, d.month, d.day, 0, 0, 0)

def _ensure_company(db: Session, company_id: int) -> None:
    if db.get(Company, company_id) is None:
        raise HTTPException(status_code=404, detail={
            'error_code': 'COMPANY_NOT_FOUND',
            'company_id': company_id,
            'message': 'Empresa não encontrada',
        })

def _resolve_period(start: str | None, end: str | None) -> tuple[datetime, datetime, Period]:
    now = datetime.utcnow()

    if start is None and end is None:
        end_dt = now
        start_dt = now - timedelta(days=30)
    elif start is not None and end is None:
        start_dt = _parse_iso_date_or_datetime(start, is_end=False)
        end_dt = now
    elif start is None and end is not None:
        end_dt = _parse_iso_date_or_datetime(end, is_end=True)
        start_dt = end_dt - timedelta(days=30)
    else:
        start_dt = _parse_iso_date_or_datetime(start, is_end=False)
        end_dt = _parse_iso_date_or_datetime(end, is_end=True)

    if start_dt > end_dt:
        raise HTTPException(status_code=422, detail={
            'error_code': 'INVALID_PERIOD',
            'message': 'start não pode ser maior que end',
            'start': start_dt.date().isoformat(),
            'end': end_dt.date().isoformat(),
        })

    period = Period(start=start_dt.date().isoformat(), end=end_dt.date().isoformat())
    return start_dt, end_dt, period


def _totals_row(db: Session, company_id: int, start_dt: datetime, end_dt: datetime) -> Totals:
    q = select(
        func.coalesce(func.sum(case((Transaction.kind == "in", Transaction.amount_cents), else_=0)), 0).label("in_cents"),
        func.coalesce(func.sum(case((Transaction.kind == "out", Transaction.amount_cents), else_=0)), 0).label("out_cents"),
        func.count(Transaction.id).label("cnt"),
    ).where(
        Transaction.company_id == company_id,
        Transaction.occurred_at.is_not(None),
        Transaction.occurred_at >= start_dt,
        Transaction.occurred_at <= end_dt,
    )

    r = db.execute(q).one()
    entradas = int(r.in_cents or 0)
    saidas = int(r.out_cents or 0)
    cnt = int(r.cnt or 0)
    return Totals(
        entradas_cents=entradas,
        saidas_cents=saidas,
        saldo_cents=entradas - saidas,
        qtd_transacoes=cnt,
    )


def _by_category(db: Session, company_id: int, start_dt: datetime, end_dt: datetime) -> list[CategoryBreakdown]:
    total_cents = func.coalesce(func.sum(Transaction.amount_cents), 0).label("total_cents")

    q = (
        select(
            Transaction.category_id,
            func.coalesce(Category.name, "Sem categoria").label("category_name"),
            func.coalesce(func.sum(case((Transaction.kind == "in", Transaction.amount_cents), else_=0)), 0).label("in_cents"),
            func.coalesce(func.sum(case((Transaction.kind == "out", Transaction.amount_cents), else_=0)), 0).label("out_cents"),
            func.count(Transaction.id).label("cnt"),
            total_cents,
        )
        .select_from(Transaction)
        .outerjoin(Category, Category.id == Transaction.category_id)
        .where(
            Transaction.company_id == company_id,
            Transaction.occurred_at.is_not(None),
            Transaction.occurred_at >= start_dt,
            Transaction.occurred_at <= end_dt,
        )
        .group_by(Transaction.category_id, Category.name)
        .order_by(total_cents.desc())
    )

    out: list[CategoryBreakdown] = []
    for r in db.execute(q).all():
        entradas = int(r.in_cents or 0)
        saidas = int(r.out_cents or 0)
        out.append(
            CategoryBreakdown(
                category_id=r.category_id,
                category_name=str(r.category_name),
                entradas_cents=entradas,
                saidas_cents=saidas,
                saldo_cents=entradas - saidas,
                qtd_transacoes=int(r.cnt or 0),
            )
        )
    return out


@router.get("/summary", response_model=SummaryResponse)
def summary(
    company_id: int = Query(..., ge=1),
    start: str | None = Query(None, description="YYYY-MM-DD ou ISO datetime"),
    end: str | None = Query(None, description="YYYY-MM-DD ou ISO datetime"),
    db: Session = Depends(get_db),
):
    start_dt, end_dt, period = _resolve_period(start, end)
    totals = _totals_row(db, company_id, start_dt, end_dt)
    by_cat = _by_category(db, company_id, start_dt, end_dt)
    return SummaryResponse(company_id=company_id, period=period, totals=totals, by_category=by_cat)


@router.get("/daily", response_model=DailyResponse)
def daily(
    company_id: int = Query(..., ge=1),
    start: str | None = Query(None),
    end: str | None = Query(None),
    db: Session = Depends(get_db),
):
    start_dt, end_dt, period = _resolve_period(start, end)

    day = func.date(Transaction.occurred_at).label("day")
    q = (
        select(
            day,
            func.coalesce(func.sum(case((Transaction.kind == "in", Transaction.amount_cents), else_=0)), 0).label("in_cents"),
            func.coalesce(func.sum(case((Transaction.kind == "out", Transaction.amount_cents), else_=0)), 0).label("out_cents"),
        )
        .where(
            Transaction.company_id == company_id,
            Transaction.occurred_at.is_not(None),
            Transaction.occurred_at >= start_dt,
            Transaction.occurred_at <= end_dt,
        )
        .group_by(day)
        .order_by(day.asc())
    )

    series: list[DailyPoint] = []
    for r in db.execute(q).all():
        entradas = int(r.in_cents or 0)
        saidas = int(r.out_cents or 0)
        series.append(
            DailyPoint(
                date=str(r.day),
                entradas_cents=entradas,
                saidas_cents=saidas,
                saldo_cents=entradas - saidas,
            )
        )

    return DailyResponse(company_id=company_id, period=period, series=series)


@router.get("/context", response_model=ContextResponse)
def context(
    company_id: int = Query(..., ge=1),
    start: str | None = Query(None),
    end: str | None = Query(None),
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    start_dt, end_dt, period = _resolve_period(start, end)
    totals = _totals_row(db, company_id, start_dt, end_dt)
    by_cat = _by_category(db, company_id, start_dt, end_dt)

    q = (
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
            Transaction.company_id == company_id,
            Transaction.occurred_at.is_not(None),
            Transaction.occurred_at >= start_dt,
            Transaction.occurred_at <= end_dt,
        )
        .order_by(Transaction.occurred_at.desc())
        .limit(limit)
    )

    recent: list[TransactionBrief] = []
    for r in db.execute(q).all():
        recent.append(
            TransactionBrief(
                id=r.id,
                occurred_at=r.occurred_at,
                kind=r.kind,
                amount_cents=int(r.amount_cents),
                category_id=r.category_id,
                category_name=str(r.category_name),
                description=r.description or "",
            )
        )

    return ContextResponse(
        company_id=company_id,
        period=period,
        totals=totals,
        by_category=by_cat,
        recent_transactions=recent,
    )


@router.get("/top-categories", response_model=TopCategoriesResponse)
def top_categories(
    company_id: int,
    start: str | None = None,
    end: str | None = None,
    metric: str = "saidas",
    limit: int = 5,
    db: Session = Depends(get_db),
):
    _ensure_company(db, company_id)
    start_dt, end_dt, period = _resolve_period(start, end)
    items = _by_category(db, company_id, start_dt, end_dt)

    m = (metric or "saidas").lower().strip()
    if m not in ("entradas", "saidas", "saldo"):
        raise HTTPException(status_code=422, detail={
            "error_code": "INVALID_METRIC",
            "message": "metric inválida (use: entradas | saidas | saldo)",
            "value": metric,
        })

    key = (lambda c: c.entradas_cents) if m == "entradas" else (lambda c: c.saidas_cents) if m == "saidas" else (lambda c: abs(c.saldo_cents))
    items = sorted(items, key=key, reverse=True)[: max(1, min(limit, 20))]

    return TopCategoriesResponse(company_id=company_id, period=period, metric=m, items=items)


# === AI Consult PDF (proxy do /ai/consult) ===
_DEJAVU_TTF = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def _pdf_font_name():
    if os.path.exists(_DEJAVU_TTF):
        try:
            pdfmetrics.registerFont(TTFont("DejaVu", _DEJAVU_TTF))
        except Exception:
            pass
        return "DejaVu"
    return "Helvetica"

def _build_pdf_bytes(title: str, payload: dict, consult: dict) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    font = _pdf_font_name()
    width, height = A4

    c.setTitle(title)
    c.setFont(font, 16)
    c.drawString(20*mm, height - 20*mm, title)

    c.setFont(font, 10)
    generated_at = _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    y = height - 30*mm
    c.drawString(20*mm, y, f"Gerado em: {generated_at}")
    y -= 8*mm
    c.drawString(20*mm, y, f"company_id: {payload.get('company_id')}")
    y -= 8*mm
    # compat: period{start,end} OU start/end no root; fallback consult.period
    period = {}
    _p = payload.get('period')
    if isinstance(_p, dict):
        period.update(_p)
    if payload.get('start') and not period.get('start'):
        period['start'] = payload.get('start')
    if payload.get('end') and not period.get('end'):
        period['end'] = payload.get('end')
    if not period.get('start') and not period.get('end'):
        _cp = consult.get('period') if isinstance(consult, dict) else None
        if isinstance(_cp, dict) and (_cp.get('start') or _cp.get('end')):
            period = _cp
    c.drawString(20*mm, y, f"period: {period.get('start')} → {period.get('end')}")
    y -= 12*mm

    c.setFont(font, 9)
    text = c.beginText(20*mm, y)
    text.setLeading(12)

    dumped = json.dumps(consult, ensure_ascii=False, indent=2)
    for ln in dumped.splitlines():
        if text.getY() < 20*mm:
            c.drawText(text)
            c.showPage()
            c.setFont(font, 9)
            text = c.beginText(20*mm, height - 20*mm)
            text.setLeading(12)
        text.textLine(ln[:180])

    c.drawText(text)
    c.showPage()
    c.save()
    return buf.getvalue()

@router.post(
    "/ai-consult/pdf",
    summary="Gera PDF do /ai/consult (proxy)",
    responses={200: {"content": {"application/pdf": {}}}},
)
async def report_ai_consult_pdf(request: Request, payload: dict = Body(...)):
    base = str(request.base_url).rstrip("/")
    root = request.scope.get("root_path", "") or ""
    url = f"{base}{root}/ai/consult"

    # compat: /reports/ai-consult/pdf aceita {'period': {'start','end'}};
    # /ai/consult espera start/end no topo.
    payload_in = payload or {}
    payload_consult = dict(payload_in)
    _p = payload_consult.get('period') or {}
    if isinstance(_p, dict):
        if 'start' not in payload_consult and _p.get('start'):
            payload_consult['start'] = _p.get('start')
        if 'end' not in payload_consult and _p.get('end'):
            payload_consult['end'] = _p.get('end')
    payload_consult.pop('period', None)

    headers = {}
    auth = request.headers.get("authorization")
    if auth:
        headers["authorization"] = auth

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, json=payload_consult, headers=headers)

    if r.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail={"msg": "falha ao chamar /ai/consult", "status": r.status_code, "body": r.text[:500]},
        )

    consult = r.json()
    pdf = _build_pdf_bytes("IA-CNPJ — Relatório AI Consult", payload_in, consult)

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="ai-consult.pdf"'},
    )
