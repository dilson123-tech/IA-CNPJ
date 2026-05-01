import json
import httpx

base = "http://127.0.0.1:8131"

login = httpx.post(
    f"{base}/auth/login",
    json={"username": "dev", "password": "dev"},
    timeout=20,
)
print("LOGIN STATUS:", login.status_code)
print("LOGIN BODY:", login.text)

token = login.json().get("access_token", "")
if not token:
    raise SystemExit("Sem token no login.")

checkout = httpx.post(
    f"{base}/billing/create-checkout",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "package_code": "founder_100",
        "billing_type": "PIX",
        "customer_name": "Dilson Pereira",
        "customer_email": "comprador@test.com",
        "customer_cpf_cnpj": "68518773920"
    },
    timeout=30,
)

print("CHECKOUT STATUS:", checkout.status_code)
print("CHECKOUT BODY:")
try:
    print(json.dumps(checkout.json(), indent=2, ensure_ascii=False))
except Exception:
    print(checkout.text)
