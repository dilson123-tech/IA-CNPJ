from typing import Any

import httpx

from app.core.settings import settings


class MercadoPagoClient:
    def __init__(self) -> None:
        self.enabled = bool(settings.MERCADOPAGO_ENABLED)
        self.base_url = settings.MERCADOPAGO_BASE_URL.rstrip("/")
        self.access_token = settings.MERCADOPAGO_ACCESS_TOKEN
        self.timeout_s = settings.MERCADOPAGO_TIMEOUT_S

    def create_checkout_preference(
        self,
        *,
        title: str,
        quantity: int,
        unit_price: float,
        external_reference: str,
        payer_name: str | None = None,
        payer_email: str | None = None,
    ) -> dict[str, Any]:
        if not self.enabled:
            return {
                "sandbox": True,
                "status": "pending",
                "provider_reference": None,
                "payment_url": None,
                "sandbox_message": "Mercado Pago ainda não configurado. Checkout em modo fundação.",
            }

        payload: dict[str, Any] = {
            "items": [
                {
                    "title": title,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "currency_id": "BRL",
                }
            ],
            "external_reference": external_reference,
            "back_urls": {
                "success": "https://example.com/success",
                "failure": "https://example.com/failure",
                "pending": "https://example.com/pending",
            },
            "notification_url": "https://example.com/webhook-test",
        }

        if payer_name or payer_email:
            payload["payer"] = {}
            if payer_name:
                payload["payer"]["name"] = payer_name
            if payer_email:
                payload["payer"]["email"] = payer_email

        with httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout_s,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
        ) as client:
            response = client.post("/checkout/preferences", json=payload)
            print("MP STATUS:", response.status_code)
            print("MP BODY:", response.text)
            response.raise_for_status()
            data = response.json()

        return {
            "sandbox": False,
            "status": "pending",
            "provider_reference": data.get("id"),
            "payment_url": data.get("init_point") or data.get("sandbox_init_point"),
            "sandbox_message": None,
            "raw": data,
        }
