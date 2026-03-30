from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import SessionLocal
from app.core.security import hash_password
from app.models.tenant import Tenant, TenantMember
from app.models.user import User
from sqlalchemy import text


def parse_args():
    parser = argparse.ArgumentParser(description="Provisiona cliente no IA-CNPJ")
    parser.add_argument("--tenant-name", required=True, help="Nome do tenant/empresa cliente")
    parser.add_argument("--email", required=True, help="Email do usuário principal")
    parser.add_argument("--password", required=True, help="Senha inicial do usuário")
    parser.add_argument("--plan", default="basic", help="Plano do tenant (default: basic)")
    parser.add_argument("--status", default="trial", help="Status do tenant (default: trial)")
    parser.add_argument("--role", default="owner", help="Role do membro (default: owner)")
    return parser.parse_args()


def main():
    args = parse_args()
    db = SessionLocal()
    db.execute(text("SET app.tenant_id = '1'"))
    db.commit()

    # 🔓 modo admin (bypass RLS)
    db.execute(text("SET row_security = off"))

    try:
        email = args.email.strip().lower()
        tenant_name = args.tenant_name.strip()

        if not tenant_name:
            raise SystemExit("ERRO: --tenant-name vazio")
        if not email:
            raise SystemExit("ERRO: --email vazio")
        if not args.password.strip():
            raise SystemExit("ERRO: --password vazio")

        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise SystemExit(f"ERRO: já existe user com email {email}")

        existing_member = db.query(TenantMember).filter(TenantMember.email == email).first()
        if existing_member:
            raise SystemExit(f"ERRO: já existe tenant_member com email {email}")

        existing_tenant = db.query(Tenant).filter(Tenant.name == tenant_name).first()
        if existing_tenant:
            raise SystemExit(f"ERRO: já existe tenant com nome {tenant_name}")

        tenant = Tenant(
            name=tenant_name,
            plan=args.plan.strip(),
            status=args.status.strip(),
        )
        db.add(tenant)
        db.flush()

        user = User(
            email=email,
            password_hash=hash_password(args.password),
            is_active=True,
        )
        db.add(user)

        member = TenantMember(
            tenant_id=tenant.id,
            email=email,
            role=args.role.strip(),
        )
        db.add(member)

        db.commit()

        print("OK: cliente provisionado com sucesso")
        print(f"tenant_id={tenant.id}")
        print(f"tenant_name={tenant.name}")
        print(f"user_email={user.email}")
        print(f"member_role={member.role}")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
