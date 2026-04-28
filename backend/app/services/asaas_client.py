from typing import Any

import httpx

from app.core.settings import settings


class AsaasClient:
    def __init__(self) -> None:
        self.enabled = bool(settings.ASAAS_ENABLED)
        self.base_url = settings.ASAAS_BASE_URL.rstrip("/")
        self.api_key = settings.ASAAS_API_KEY
        self.timeout_s = settings.ASAAS_TIMEOUT_S

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

        payload = {
            "billingType": billing_type,
            "value": round(amount_cents / 100, 2),
            "description": description,
            "externalReference": external_reference,
        }

        # MVP: ainda sem customer real Asaas. Na próxima etapa criamos/recuperamos customer.
        if customer_name:
            payload["name"] = customer_name
        if customer_email:
            payload["email"] = customer_email
        if customer_cpf_cnpj:
            payload["cpfCnpj"] = customer_cpf_cnpj

        with httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout_s,
            headers={"access_token": self.api_key, "Content-Type": "application/json"},
        ) as client:
            response = client.post("/payments", json=payload)
            response.raise_for_status()
            data = response.json()

        return {
            "sandbox": False,
            "status": data.get("status", "pending").lower(),
            "provider_reference": data.get("id"),
            "payment_url": data.get("invoiceUrl"),
            "sandbox_message": None,
        }
