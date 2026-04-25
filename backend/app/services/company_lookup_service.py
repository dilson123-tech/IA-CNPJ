from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

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


def _clean_str(
    value: object,
    *,
    max_len: int | None = None,
    upper: bool = False,
) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    if upper:
        text = text.upper()

    if max_len is not None:
        text = text[:max_len]

    return text


def _parse_date(value: object) -> date | None:
    if value is None:
        return None

    if isinstance(value, date) and not isinstance(value, datetime):
        return value

    text = str(value).strip()
    if not text:
        return None

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _parse_bool(value: object) -> bool | None:
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return bool(value)

    text = str(value).strip().lower()
    if text in {"true", "1", "sim", "s", "yes", "y"}:
        return True
    if text in {"false", "0", "nao", "não", "n", "no"}:
        return False

    return None


def _parse_decimal(value: object) -> Decimal | None:
    if value is None:
        return None

    if isinstance(value, Decimal):
        return value

    if isinstance(value, (int, float)):
        return Decimal(str(value))

    text = str(value).strip()
    if not text:
        return None

    text = text.replace(".", "").replace(",", ".") if "," in text else text

    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def _pick_primary_cnae(data: dict) -> tuple[str | None, str | None]:
    code = _clean_str(
        data.get("cnae_fiscal")
        or data.get("cnae_principal_codigo")
        or data.get("cnae_principal"),
        max_len=20,
    )
    desc = _clean_str(
        data.get("cnae_fiscal_descricao")
        or data.get("cnae_principal_descricao"),
        max_len=200,
    )

    if code or desc:
        return code, desc

    atividade_principal = data.get("atividade_principal")

    if isinstance(atividade_principal, list) and atividade_principal:
        atividade_principal = atividade_principal[0]

    if isinstance(atividade_principal, dict):
        code = _clean_str(
            atividade_principal.get("code")
            or atividade_principal.get("codigo"),
            max_len=20,
        )
        desc = _clean_str(
            atividade_principal.get("text")
            or atividade_principal.get("descricao"),
            max_len=200,
        )

    return code, desc


def _build_company_business_data(*, normalized_cnpj: str, data: dict) -> dict:
    razao_social = _clean_str(
        data.get("razao_social")
        or data.get("nome")
        or data.get("company_name"),
        max_len=200,
    )

    if not razao_social:
        raise HTTPException(status_code=503, detail="Provedor de CNPJ retornou dados incompletos")

    cnae_principal_codigo, cnae_principal_descricao = _pick_primary_cnae(data)

    return {
        "cnpj": normalized_cnpj,
        "razao_social": razao_social,
        "nome_fantasia": _clean_str(
            data.get("nome_fantasia")
            or data.get("fantasia"),
            max_len=200,
        ),
        "situacao_cadastral": _clean_str(
            data.get("descricao_situacao_cadastral")
            or data.get("situacao_cadastral")
            or data.get("descricao_situacao"),
            max_len=50,
        ),
        "data_situacao_cadastral": _parse_date(data.get("data_situacao_cadastral")),
        "descricao_motivo_situacao_cadastral": _clean_str(
            data.get("descricao_motivo_situacao_cadastral"),
            max_len=120,
        ),
        "situacao_especial": _clean_str(
            data.get("situacao_especial"),
            max_len=120,
        ),
        "data_situacao_especial": _parse_date(data.get("data_situacao_especial")),
        "natureza_juridica": _clean_str(
            data.get("natureza_juridica")
            or data.get("descricao_natureza_juridica"),
            max_len=120,
        ),
        "codigo_natureza_juridica": _clean_str(
            data.get("codigo_natureza_juridica"),
            max_len=10,
        ),
        "porte": _clean_str(
            data.get("porte")
            or data.get("descricao_porte"),
            max_len=50,
        ),
        "matriz_filial": _clean_str(
            data.get("descricao_identificador_matriz_filial")
            or data.get("identificador_matriz_filial"),
            max_len=20,
            upper=True,
        ),
        "opcao_pelo_simples": _parse_bool(data.get("opcao_pelo_simples")),
        "opcao_pelo_mei": _parse_bool(data.get("opcao_pelo_mei")),
        "capital_social": _parse_decimal(data.get("capital_social")),
        "data_abertura": _parse_date(
            data.get("data_inicio_atividade")
            or data.get("data_abertura")
            or data.get("abertura"),
        ),
        "data_baixa": _parse_date(
            data.get("data_baixa")
            or data.get("baixa"),
        ),
        "cnae_principal_codigo": cnae_principal_codigo,
        "cnae_principal_descricao": cnae_principal_descricao,
        "municipio": _clean_str(
            data.get("municipio")
            or data.get("cidade"),
            max_len=100,
        ),
        "codigo_municipio_ibge": _clean_str(
            data.get("codigo_municipio_ibge"),
            max_len=10,
        ),
        "uf": _clean_str(
            data.get("uf")
            or data.get("estado"),
            max_len=2,
            upper=True,
        ),
        "cep": _clean_str(data.get("cep"), max_len=20),
        "bairro": _clean_str(data.get("bairro"), max_len=100),
        "logradouro": _clean_str(
            data.get("logradouro")
            or data.get("descricao_tipo_de_logradouro"),
            max_len=150,
        ),
        "numero": _clean_str(data.get("numero"), max_len=30),
        "complemento": _clean_str(data.get("complemento"), max_len=120),
        "email": _clean_str(data.get("email"), max_len=200),
        "ddd_telefone_1": _clean_str(data.get("ddd_telefone_1"), max_len=20),
        "ddd_telefone_2": _clean_str(data.get("ddd_telefone_2"), max_len=20),
        "qsa": data.get("qsa") if isinstance(data.get("qsa"), list) else None,
    }


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


def _apply_company_business_data(company: Company, company_data: dict) -> Company:
    fields = (
        "razao_social",
        "nome_fantasia",
        "situacao_cadastral",
        "data_situacao_cadastral",
        "descricao_motivo_situacao_cadastral",
        "situacao_especial",
        "data_situacao_especial",
        "natureza_juridica",
        "codigo_natureza_juridica",
        "porte",
        "matriz_filial",
        "opcao_pelo_simples",
        "opcao_pelo_mei",
        "capital_social",
        "data_abertura",
        "data_baixa",
        "cnae_principal_codigo",
        "cnae_principal_descricao",
        "municipio",
        "codigo_municipio_ibge",
        "uf",
        "cep",
        "bairro",
        "logradouro",
        "numero",
        "complemento",
        "email",
        "ddd_telefone_1",
        "ddd_telefone_2",
        "qsa",
    )

    for field in fields:
        value = company_data.get(field)
        if value is not None:
            setattr(company, field, value)

    return company


def create_company_record(
    *,
    db: Session,
    tenant_id: int,
    company_data: dict,
) -> Company:
    normalized_cnpj = normalize_cnpj(company_data.get("cnpj"))

    razao_social = _clean_str(company_data.get("razao_social"), max_len=200)
    if not razao_social:
        raise HTTPException(status_code=422, detail="Razão social obrigatória")

    company = Company(
        cnpj=normalized_cnpj,
        razao_social=razao_social,
        tenant_id=tenant_id,
    )
    _apply_company_business_data(company, company_data)
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

    return _build_company_business_data(
        normalized_cnpj=normalized_cnpj,
        data=data,
    )


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
        company_data=external,
    )
    db.commit()
    db.refresh(company)
    return company
