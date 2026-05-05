from datetime import date
from typing import Any

import httpx

from app.core.settings import settings


class AsaasClient:
    def __init__(self) -> None:
        self.enabled = bool(settings.ASAAS_ENABLED)
        self.base_url = settings.ASAAS_BASE_URL.rstrip("/")
        self.api_key = settings.ASAAS_API_KEY
        self.timeout_s = settings.ASAAS_TIMEOUT_S

    def _headers(self) -> dict[str, str]:
        return {
            "access_token": self.api_key,
            "Content-Type": "application/json",
            "accept": "application/json",
        }

    @staticmethod
    def _digits_only(value: str | None) -> str:
        return "".join(ch for ch in str(value or "") if ch.isdigit())

    def _create_customer(
        self,
        client: httpx.Client,
        *,
        customer_name: str | None,
        customer_email: str | None,
        customer_cpf_cnpj: str | None,
        external_reference: str,
    ) -> str:
        cpf_cnpj = self._digits_only(customer_cpf_cnpj)

        if not cpf_cnpj:
            raise ValueError("customer_cpf_cnpj é obrigatório para criar cliente no Asaas")

        payload: dict[str, Any] = {
            "name": customer_name or "Cliente IA-CNPJ SaaS",
            "cpfCnpj": cpf_cnpj,
            "externalReference": external_reference,
            "notificationDisabled": True,
        }

        if customer_email:
            payload["email"] = customer_email

        response = client.post("/customers", json=payload)
        response.raise_for_status()
        data = response.json()

        customer_id = str(data.get("id") or "").strip()
        if not customer_id:
            raise ValueError("Asaas não retornou id do customer")

        return customer_id

    def create_payment(
        self,
        *,
        customer_name: str | None,
        customer_email: str | None,
        customer_cpf_cnpj: str | None,
        amount_cents: int,
        billing_type: str,
        description: str,
        external_reference: str,
    ) -> dict[str, Any]:
        if not self.enabled:
            return {
                "sandbox": True,
                "status": "pending",
                "provider_reference": None,
                "payment_url": None,
                "sandbox_message": "ASAAS ainda não configurado. Checkout em modo fundação.",
            }

        effective_billing_type = "PIX" if str(billing_type or "").upper() == "PIX" else billing_type

        with httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout_s,
            headers=self._headers(),
        ) as client:
            customer_id = self._create_customer(
                client,
                customer_name=customer_name,
                customer_email=customer_email,
                customer_cpf_cnpj=customer_cpf_cnpj,
                external_reference=external_reference,
            )

            payment_payload = {
                "customer": customer_id,
                "billingType": effective_billing_type,
                "value": round(amount_cents / 100, 2),
                "dueDate": date.today().isoformat(),
                "description": description,
                "externalReference": external_reference,
            }

            payment_response = client.post("/payments", json=payment_payload)
            payment_response.raise_for_status()
            payment_data = payment_response.json()

            payment_id = str(payment_data.get("id") or "").strip()
            payment_url = payment_data.get("invoiceUrl") or payment_data.get("bankSlipUrl")

            pix_qr_code: dict[str, Any] | None = None
            if effective_billing_type == "PIX" and payment_id:
                qr_response = client.get(f"/payments/{payment_id}/pixQrCode")
                qr_response.raise_for_status()
                pix_qr_code = qr_response.json()

        return {
            "sandbox": False,
            "status": str(payment_data.get("status") or "pending").lower(),
            "provider_reference": payment_id,
            "payment_url": payment_url,
            "sandbox_message": None,
            "raw": {
                "payment": payment_data,
                "pix_qr_code": pix_qr_code,
            },
        }
