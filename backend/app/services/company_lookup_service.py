from __future__ import annotations

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.models.company import Company


def normalize_cnpj(raw: str) -> str:
    digits = "".join(ch for ch in str(raw or "") if ch.isdigit())
    if len(digits) != 14:
        raise HTTPException(status_code=422, detail="CNPJ inválido")
    return digits


def get_company_by_cnpj_local(
    *,
    db: Session,
    tenant_id: int,
    cnpj: str,
) -> Company | None:
    normalized_cnpj = normalize_cnpj(cnpj)
    return db.scalar(
        select(Company)
        .where(Company.cnpj == normalized_cnpj)
        .where(Company.tenant_id == tenant_id)
    )


def create_company_record(
    *,
    db: Session,
    tenant_id: int,
    cnpj: str,
    razao_social: str,
) -> Company:
    normalized_cnpj = normalize_cnpj(cnpj)
    social_name = (razao_social or "").strip()

    if not social_name:
        raise HTTPException(status_code=422, detail="Razão social obrigatória")

    company = Company(
        cnpj=normalized_cnpj,
        razao_social=social_name,
        tenant_id=tenant_id,
    )
    db.add(company)
    db.flush()
    return company


def _lookup_company_external(cnpj: str) -> dict | None:
    provider = (settings.CNPJ_LOOKUP_PROVIDER or "").strip().lower()
    normalized_cnpj = normalize_cnpj(cnpj)

    if provider in ("", "none", "off", "disabled"):
        return None

    if provider != "brasilapi":
        raise HTTPException(status_code=503, detail="Provedor de CNPJ não suportado")

    url = f"{settings.CNPJ_LOOKUP_BASE_URL.rstrip('/')}/{normalized_cnpj}"

    try:
        with httpx.Client(timeout=settings.CNPJ_LOOKUP_TIMEOUT_S) as client:
            response = client.get(url, headers={"Accept": "application/json"})
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Timeout ao consultar provedor de CNPJ")
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="Falha de comunicação com provedor de CNPJ")

    if response.status_code == 404:
        return None

    if response.status_code >= 400:
        raise HTTPException(status_code=503, detail="Provedor de CNPJ indisponível")

    try:
        data = response.json()
    except Exception:
        raise HTTPException(status_code=503, detail="Resposta inválida do provedor de CNPJ")

    razao_social = (
        str(
            data.get("razao_social")
            or data.get("nome")
            or data.get("company_name")
            or ""
        ).strip()
    )

    if not razao_social:
        raise HTTPException(status_code=503, detail="Provedor de CNPJ retornou dados incompletos")

    return {
        "cnpj": normalized_cnpj,
        "razao_social": razao_social,
    }


def get_or_create_company_by_cnpj(
    *,
    db: Session,
    tenant_id: int,
    cnpj: str,
) -> Company:
    company = get_company_by_cnpj_local(
        db=db,
        tenant_id=tenant_id,
        cnpj=cnpj,
    )
    if company:
        return company

    external = _lookup_company_external(cnpj)
    if not external:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    company = create_company_record(
        db=db,
        tenant_id=tenant_id,
        cnpj=external["cnpj"],
        razao_social=external["razao_social"],
    )
    db.commit()
    db.refresh(company)
    return company
