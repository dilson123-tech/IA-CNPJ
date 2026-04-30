from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
import httpx

from app.core.tenant import get_current_tenant_id
from app.db import get_db
from app.schemas.billing import CreateCheckoutRequest, CreateCheckoutResponse, PurchaseHistoryItem
from app.services.billing_service import BillingService
from app.models.credit_purchase import CreditPurchase

router = APIRouter(prefix="/billing", tags=["Billing"])
public_router = APIRouter(prefix="/billing", tags=["Billing Public"])


@router.post("/create-checkout", response_model=CreateCheckoutResponse)
def create_checkout(
    payload: CreateCheckoutRequest,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    try:
        purchase = BillingService(db).create_checkout(tenant_id=tenant_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        detail = {
            "message": "Gateway de pagamento recusou a operação.",
            "provider_status": exc.response.status_code,
            "provider_message": exc.response.text,
        }
        try:
            body = exc.response.json()
            detail["provider_code"] = body.get("code")
            detail["provider_message"] = body.get("message") or detail["provider_message"]
            detail["blocked_by"] = body.get("blocked_by")
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=detail) from exc

    return CreateCheckoutResponse(
        purchase_id=purchase.id,
        package_code=purchase.package_code,
        credits_amount=purchase.credits_amount,
        amount_cents=purchase.amount_cents,
        currency=purchase.currency,
        billing_type=purchase.billing_type,
        status=purchase.status,
        provider=purchase.provider,
        payment_url=purchase.payment_url,
        provider_reference=purchase.provider_reference,
        sandbox_message=getattr(purchase, "_sandbox_message", None),
    )


@public_router.post("/webhook/asaas")
async def asaas_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    service = BillingService(db)
    service.validate_asaas_webhook_token(dict(request.headers))
    payload = await request.json()
    return service.handle_asaas_webhook(payload)


@router.get("/purchases/me", response_model=list[PurchaseHistoryItem])
def list_my_purchases(
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    rows = (
        db.query(CreditPurchase)
        .filter(CreditPurchase.tenant_id == tenant_id)
        .order_by(CreditPurchase.id.desc())
        .limit(50)
        .all()
    )

    return [
        PurchaseHistoryItem(
            purchase_id=row.id,
            package_code=row.package_code,
            credits_amount=row.credits_amount,
            amount_cents=row.amount_cents,
            currency=row.currency,
            billing_type=row.billing_type,
            status=row.status,
            provider=row.provider,
            payment_url=row.payment_url,
            provider_reference=row.provider_reference,
            customer_name=row.customer_name,
            customer_email=row.customer_email,
            customer_cpf_cnpj=row.customer_cpf_cnpj,
            paid_at=row.paid_at.isoformat() if row.paid_at else None,
            created_at=row.created_at.isoformat() if row.created_at else None,
        )
        for row in rows
    ]


@public_router.post("/webhook/mercadopago")
async def mercadopago_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    payload = await request.json()
    return BillingService(db).handle_mercadopago_webhook(payload)
