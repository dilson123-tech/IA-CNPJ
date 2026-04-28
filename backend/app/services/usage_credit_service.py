from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.usage_credit import TenantUsageCredit


class UsageCreditService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_wallet(self, tenant_id: int) -> TenantUsageCredit:
        wallet = (
            self.db.query(TenantUsageCredit)
            .filter(TenantUsageCredit.tenant_id == tenant_id)
            .first()
        )

        if wallet:
            return wallet

        wallet = TenantUsageCredit(
            tenant_id=tenant_id,
            balance=10,
            consumed=0,
            source="starter",
        )
        self.db.add(wallet)
        self.db.flush()

        return wallet

    def get_balance(self, tenant_id: int) -> TenantUsageCredit:
        wallet = self.get_or_create_wallet(tenant_id)
        self.db.commit()
        self.db.refresh(wallet)
        return wallet

    def consume(self, tenant_id: int, amount: int = 1) -> TenantUsageCredit:
        wallet = self.get_or_create_wallet(tenant_id)

        if wallet.balance < amount:
            raise HTTPException(
                status_code=402,
                detail="Créditos insuficientes para realizar esta consulta.",
            )

        wallet.balance -= amount
        wallet.consumed += amount

        self.db.commit()
        self.db.refresh(wallet)

        return wallet
