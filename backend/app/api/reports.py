from __future__ import annotations

from datetime import datetime, timedelta, date, time, timezone
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, case
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.transaction import Transaction
from app.models.category import Category
from app.schemas.reports import (
    Period, Totals, CategoryBreakdown,
    SummaryResponse, DailyPoint, DailyResponse,
    TransactionBrief, ContextResponse
)

router = APIRouter(prefix="/reports", tags=["reports"])


def _parse_iso_date_or_datetime(s: str, *, is_end: bool) -> datetime:
    s = s.strip()
    # datetime ISO
    if "T" in s:
        # suporta Z
        s2 = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s2)
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    # date YYYY-MM-DD
    d = date.fromisoformat(s)
    return datetime.combine(d, time.max if is_end else time.min)


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
        raise HTTPException(status_code=400, detail="start must be <= end")

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
