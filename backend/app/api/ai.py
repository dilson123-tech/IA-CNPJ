from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.tenant import get_current_tenant_id
from app.deps import get_db
from app.services.ai_consult_service import run_ai_consult
from app.api.transaction import suggest_categories as tx_suggest_categories, apply_suggestions as tx_apply_suggestions
from app.schemas.ai import (
    AiConsultRequest,
    AiConsultResponse,
    AISuggestCategoriesRequest,
    AISuggestCategoriesResponse,
    AIApplySuggestionsRequest,
    AIApplySuggestionsResponse,
)

router = APIRouter(prefix="/ai", tags=["ai"])
logger = logging.getLogger(__name__)


def _fmt_brl(cents: int) -> str:
    v = cents / 100.0
    # formatação simples, sem locale
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@router.post("/consult", response_model=AiConsultResponse)
def consult(payload: AiConsultRequest, request: Request, db: Session = Depends(get_db), tenant_id: int = Depends(get_current_tenant_id)):
    request_id = request.headers.get('x-request-id') or uuid4().hex
    try:
        result = run_ai_consult(
            db=db,
            payload=payload,
            tenant_id=tenant_id,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("ai_consult_failed request_id=%s company_id=%s", request_id, getattr(payload, "company_id", None))
        raise HTTPException(status_code=500, detail=f"Erro interno em /ai/consult: {e}")


@router.post("/suggest-categories", response_model=AISuggestCategoriesResponse)
def ai_suggest_categories(
    payload: AISuggestCategoriesRequest,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    items = tx_suggest_categories(
        company_id=payload.company_id,
        start=payload.start,
        end=payload.end,
        limit=payload.limit,
        include_no_match=payload.include_no_match,
        db=db,
        tenant_id=tenant_id,
    )
    return {
        "company_id": payload.company_id,
        "period": {"start": payload.start, "end": payload.end},
        "items": items,
    }


@router.post("/apply-suggestions", response_model=AIApplySuggestionsResponse)
def ai_apply_suggestions(
    payload: AIApplySuggestionsRequest,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    return tx_apply_suggestions(
        company_id=payload.company_id,
        start=payload.start,
        end=payload.end,
        limit=payload.limit,
        dry_run=payload.dry_run,
        include_no_match=payload.include_no_match,
        db=db,
        tenant_id=tenant_id,
    )

