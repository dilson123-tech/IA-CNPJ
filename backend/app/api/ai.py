from __future__ import annotations

import logging
import os
import re
import traceback
from datetime import datetime, timedelta, timezone
from time import perf_counter
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api import reports as rep
from app.core.tenant import get_current_tenant_id
from app.deps import get_db
from app.models.transaction import Transaction
from app.models.category import Category
from app.services.ai_consult_service import run_ai_consult
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
    t0 = perf_counter()
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
def ai_suggest_categories(payload: AISuggestCategoriesRequest, db: Session = Depends(get_db)):
    raise HTTPException(status_code=501, detail="suggest-categories temporarily disabled (lint fix)")


@router.post("/apply-suggestions", response_model=AIApplySuggestionsResponse)
def ai_apply_suggestions(payload: AIApplySuggestionsRequest, db: Session = Depends(get_db)):
    raise HTTPException(status_code=501, detail="apply-suggestions temporarily disabled (lint fix)")

