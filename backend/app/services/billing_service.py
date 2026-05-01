from datetime import datetime, timezone
import re

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.models.credit_purchase import CreditPurchase
from app.models.tenant import Tenant  # noqa: F401
from app.models.usage_credit import TenantUsageCredit  # noqa: F401
from app.schemas.billing import CreateCheckoutRequest
from app.services.asaas_client import AsaasClient
from app.services.billing_catalog import get_package
from app.services.mercadopago_client import MercadoPagoClient
from app.services.pagbank_client import PagBankClient
from app.services.usage_credit_service import UsageCreditService


class BillingService:
    def __init__(self, db: Session):
        self.db = db
        self.asaas = AsaasClient()
        self.mercadopago = MercadoPagoClient()
        self.pagbank = PagBankClient()

    def create_checkout(self, tenant_id: int, payload: CreateCheckoutRequest) -> CreditPurchase:
        pkg = get_package(payload.package_code)

        provider_name = "pagbank" if self.pagbank.enabled else "mercadopago" if self.mercadopago.enabled else "asaas"
        effective_billing_type = "PIX" if provider_name == "pagbank" else payload.billing_type

        purchase = CreditPurchase(
            tenant_id=tenant_id,
            package_code=pkg["package_code"],
            credits_amount=pkg["credits_amount"],
            amount_cents=pkg["amount_cents"],
            currency=pkg["currency"],
            provider=provider_name,
            billing_type=effective_billing_type,
            status="pending",
            customer_name=payload.customer_name,
            customer_email=payload.customer_email,
            customer_cpf_cnpj=payload.customer_cpf_cnpj,
        )
        self.db.add(purchase)
        self.db.flush()

        external_reference = f"credit_purchase:{purchase.id}:tenant:{tenant_id}"

        if self.pagbank.enabled:
            provider_data = self.pagbank.create_pix_order(
                title=f"{pkg['credits_amount']} créditos - IA-CNPJ SaaS",
                amount_cents=pkg["amount_cents"],
                external_reference=external_reference,
                customer_name=payload.customer_name,
                customer_email=payload.customer_email,
                customer_cpf_cnpj=payload.customer_cpf_cnpj,
            )
        elif self.mercadopago.enabled:
            provider_data = self.mercadopago.create_checkout_preference(
                title=f"{pkg['credits_amount']} créditos - IA-CNPJ SaaS",
                quantity=1,
                unit_price=round(pkg["amount_cents"] / 100, 2),
                external_reference=external_reference,
                payer_name=payload.customer_name,
                payer_email=payload.customer_email,
            )
        else:
            provider_data = self.asaas.create_payment(
                customer_name=payload.customer_name,
                customer_email=payload.customer_email,
                customer_cpf_cnpj=payload.customer_cpf_cnpj,
                amount_cents=pkg["amount_cents"],
                billing_type=payload.billing_type,
                description=f"Compra de {pkg['credits_amount']} créditos - IA-CNPJ SaaS",
                external_reference=external_reference,
            )

        purchase.provider_reference = provider_data.get("provider_reference")
        purchase.payment_url = provider_data.get("payment_url")
        purchase.status = provider_data.get("status") or "pending"

        self.db.commit()
        self.db.refresh(purchase)

        purchase._sandbox_message = provider_data.get("sandbox_message")
        return purchase

    @staticmethod
    def validate_asaas_webhook_token(headers: dict) -> None:
        expected = str(settings.ASAAS_WEBHOOK_TOKEN or "").strip()
        if not expected:
            return

        candidates = [
            str(headers.get("asaas-access-token") or "").strip(),
            str(headers.get("x-asaas-access-token") or "").strip(),
            str(headers.get("x-webhook-token") or "").strip(),
            str(headers.get("authorization") or "").replace("Bearer ", "").strip(),
        ]

        if expected not in candidates:
            raise HTTPException(status_code=401, detail="Invalid Asaas webhook token")

    def _find_purchase_from_payload(self, payload: dict) -> CreditPurchase | None:
        payment = payload.get("payment") or payload or {}

        external_candidates = [
            str(payment.get("externalReference") or "").strip(),
            str(payload.get("externalReference") or "").strip(),
            str(payment.get("external_reference") or "").strip(),
            str(payload.get("external_reference") or "").strip(),
        ]

        purchase_id = None
        for candidate in external_candidates:
            if not candidate:
                continue
            match = re.search(r"credit_purchase:(\d+)", candidate)
            if match:
                purchase_id = int(match.group(1))
                break

        if purchase_id:
            purchase = (
                self.db.query(CreditPurchase)
                .filter(CreditPurchase.id == purchase_id)
                .first()
            )
            if purchase:
                return purchase

        provider_reference = str(
            payment.get("id")
            or payload.get("paymentId")
            or payload.get("id")
            or ""
        ).strip()

        if provider_reference:
            purchase = (
                self.db.query(CreditPurchase)
                .filter(CreditPurchase.provider_reference == provider_reference)
                .first()
            )
            if purchase:
                return purchase

        return None

    @staticmethod
    def _is_paid_event(payload: dict) -> bool:
        payment = payload.get("payment") or payload
        event = str(payload.get("event") or "").upper()
        status = str(payment.get("status") or payload.get("status") or "").upper()

        return event in {
            "PAYMENT_RECEIVED",
            "PAYMENT_CONFIRMED",
            "PAYMENT_UPDATED",
        } or status in {
            "RECEIVED",
            "CONFIRMED",
            "RECEIVED_IN_CASH",
        }

    def apply_paid_purchase(self, purchase: CreditPurchase) -> tuple[CreditPurchase, bool]:
        if purchase.credits_applied_at:
            return purchase, False

        wallet = UsageCreditService(self.db).get_or_create_wallet(purchase.tenant_id)
        wallet.balance += int(purchase.credits_amount)

        now_utc = datetime.now(timezone.utc)
        purchase.status = "paid"
        if not purchase.paid_at:
            purchase.paid_at = now_utc
        purchase.credits_applied_at = now_utc

        self.db.commit()
        self.db.refresh(purchase)
        self.db.refresh(wallet)

        return purchase, True

    def handle_asaas_webhook(self, payload: dict) -> dict:
        payment = payload.get("payment") or payload or {}
        purchase = self._find_purchase_from_payload(payload)
        if not purchase:
            return {
                "ok": True,
                "matched": False,
                "applied": False,
                "reason": "purchase_not_found",
                "debug_external_reference": (
                    payment.get("externalReference")
                    or payload.get("externalReference")
                    or payment.get("external_reference")
                    or payload.get("external_reference")
                ),
                "debug_provider_reference": (
                    payment.get("id")
                    or payload.get("paymentId")
                    or payload.get("id")
                ),
            }

        payment = payload.get("payment") or payload
        provider_reference = str(
            payment.get("id")
            or payload.get("paymentId")
            or payload.get("id")
            or ""
        ).strip()

        if provider_reference and not purchase.provider_reference:
            purchase.provider_reference = provider_reference

        incoming_status = str(payment.get("status") or payload.get("status") or "").lower().strip()
        if incoming_status:
            purchase.status = incoming_status

        if not self._is_paid_event(payload):
            self.db.commit()
            self.db.refresh(purchase)
            return {
                "ok": True,
                "matched": True,
                "applied": False,
                "purchase_id": purchase.id,
                "status": purchase.status,
                "reason": "event_not_paid",
            }

        purchase, applied = self.apply_paid_purchase(purchase)

        return {
            "ok": True,
            "matched": True,
            "applied": applied,
            "purchase_id": purchase.id,
            "tenant_id": purchase.tenant_id,
            "credits_amount": purchase.credits_amount,
            "status": purchase.status,
        }


    def handle_pagbank_webhook(self, payload: dict) -> dict:
        reference_id = str(payload.get("reference_id") or "").strip()
        order_id = str(payload.get("id") or "").strip()
        charges = payload.get("charges") or []
        charge = charges[0] if charges else {}
        charge_id = str(charge.get("id") or "").strip()
        charge_status = str(charge.get("status") or "").upper().strip()

        purchase = None

        if reference_id:
            match = re.search(r"credit_purchase:(\d+)", reference_id)
            if match:
                purchase = (
                    self.db.query(CreditPurchase)
                    .filter(CreditPurchase.id == int(match.group(1)))
                    .first()
                )

        if not purchase and order_id:
            purchase = (
                self.db.query(CreditPurchase)
                .filter(CreditPurchase.provider_reference == order_id)
                .first()
            )

        if not purchase and charge_id:
            purchase = (
                self.db.query(CreditPurchase)
                .filter(CreditPurchase.provider_reference == charge_id)
                .first()
            )

        if not purchase:
            return {
                "ok": True,
                "matched": False,
                "applied": False,
                "reason": "purchase_not_found",
                "debug_reference_id": reference_id or None,
                "debug_order_id": order_id or None,
                "debug_charge_id": charge_id or None,
            }

        if order_id and not purchase.provider_reference:
            purchase.provider_reference = order_id

        if charge_status:
            purchase.status = charge_status.lower()

        if charge_status != "PAID":
            self.db.commit()
            self.db.refresh(purchase)
            return {
                "ok": True,
                "matched": True,
                "applied": False,
                "purchase_id": purchase.id,
                "status": purchase.status,
                "reason": "event_not_paid",
            }

        purchase, applied = self.apply_paid_purchase(purchase)

        return {
            "ok": True,
            "matched": True,
            "applied": applied,
            "purchase_id": purchase.id,
            "tenant_id": purchase.tenant_id,
            "credits_amount": purchase.credits_amount,
            "status": purchase.status,
            "provider_reference": purchase.provider_reference,
        }


    def handle_mercadopago_webhook(self, payload: dict) -> dict:
        action = str(payload.get("action") or "").lower()
        data = payload.get("data") or {}
        provider_reference = str(data.get("id") or payload.get("id") or "").strip()
        external_reference = str(
            payload.get("external_reference")
            or payload.get("externalReference")
            or ""
        ).strip()

        fake_payload = {
            "event": action.upper(),
            "payment": {
                "id": provider_reference,
                "status": "approved" if action == "payment.updated" else payload.get("status", ""),
                "externalReference": external_reference,
            },
        }

        purchase = self._find_purchase_from_payload(fake_payload)
        if not purchase:
            if provider_reference:
                purchase = (
                    self.db.query(CreditPurchase)
                    .filter(CreditPurchase.provider_reference == provider_reference)
                    .first()
                )

        if not purchase:
            return {
                "ok": True,
                "matched": False,
                "applied": False,
                "reason": "purchase_not_found",
                "debug_external_reference": external_reference or None,
                "debug_provider_reference": provider_reference or None,
            }

        if provider_reference and not purchase.provider_reference:
            purchase.provider_reference = provider_reference

        status = str(payload.get("status") or "").lower().strip()
        if status:
            purchase.status = status

        is_paid = status in {"approved", "accredited"} or action in {"payment.updated", "payment.created"}

        if not is_paid:
            self.db.commit()
            self.db.refresh(purchase)
            return {
                "ok": True,
                "matched": True,
                "applied": False,
                "purchase_id": purchase.id,
                "status": purchase.status,
                "reason": "event_not_paid",
            }

        purchase, applied = self.apply_paid_purchase(purchase)

        return {
            "ok": True,
            "matched": True,
            "applied": applied,
            "purchase_id": purchase.id,
            "tenant_id": purchase.tenant_id,
            "credits_amount": purchase.credits_amount,
            "status": purchase.status,
        }
