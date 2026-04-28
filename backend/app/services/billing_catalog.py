PACKAGES = {
    "starter_30": {
        "package_code": "starter_30",
        "credits_amount": 30,
        "amount_cents": 900,
        "currency": "BRL",
        "label": "Entrada",
    },
    "founder_100": {
        "package_code": "founder_100",
        "credits_amount": 100,
        "amount_cents": 2900,
        "currency": "BRL",
        "label": "Fundador",
    },
    "ops_300": {
        "package_code": "ops_300",
        "credits_amount": 300,
        "amount_cents": 7900,
        "currency": "BRL",
        "label": "Operação",
    },
}


def get_package(package_code: str) -> dict:
    key = (package_code or "").strip()
    pkg = PACKAGES.get(key)
    if not pkg:
        raise ValueError("Pacote de créditos inválido.")
    return pkg
