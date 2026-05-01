from typing import Any
from datetime import datetime, timedelta, timezone

import httpx

from app.core.settings import settings


class PagBankClient:
    def __init__(self) -> None:
        self.enabled = bool(settings.PAGBANK_ENABLED)
        self.token = settings.PAGBANK_TOKEN
        self.base_url = settings.PAGBANK_BASE_URL.rstrip("/")

    def create_pix_order(
        self,
        *,
        title: str,
        amount_cents: int,
        external_reference: str,
        customer_name: str | None = None,
        customer_email: str | None = None,
        customer_cpf_cnpj: str | None = None,
    ) -> dict[str, Any]:
        if not self.enabled:
            return {
                "sandbox": True,
                "status": "pending",
                "provider_reference": None,
                "payment_url": None,
                "sandbox_message": "PagBank ainda não configurado. Checkout em modo fundação.",
            }

        expiration = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()

        payload: dict[str, Any] = {
            "reference_id": external_reference,
            "customer": {
                "name": customer_name or "Cliente IA-CNPJ SaaS",
                "email": customer_email or "comprador@test.com",
                "tax_id": customer_cpf_cnpj or "12345678909",
            },
            "items": [
                {
                    "name": title,
                    "quantity": 1,
                    "unit_amount": amount_cents,
                }
            ],
            "qr_codes": [
                {
                    "amount": {
                        "value": amount_cents,
                    },
                    "expiration_date": expiration,
                }
            ],
            "notification_urls": [
                settings.PAGBANK_WEBHOOK_URL
            ],
        }

        with httpx.Client(
            base_url=self.base_url,
            timeout=30,
            headers={
                "Authorization": f"Bearer {self.token}",
                "accept": "application/json",
                "content-type": "application/json",
            },
        ) as client:
            response = client.post("/orders", json=payload)
            print("PAGBANK STATUS:", response.status_code)
            print("PAGBANK BODY:", response.text)
            response.raise_for_status()
            data = response.json()

        payment_url = None
        qr_codes = data.get("qr_codes") or []
        if qr_codes:
            links = qr_codes[0].get("links") or []
            for link in links:
                if link.get("media") == "image/png":
                    payment_url = link.get("href")
                    break
            if not payment_url and links:
                payment_url = links[0].get("href")

        return {
            "sandbox": False,
            "status": "pending",
            "provider_reference": data.get("id"),
            "payment_url": payment_url,
            "sandbox_message": None,
            "raw": data,
        }
