from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.deps import get_db
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryOut
from app.core.tenant import get_current_tenant_id

router = APIRouter(prefix="/categories", tags=["categories"])

@router.post("", response_model=CategoryOut)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    exists = db.scalar(
        select(Category)
        .where(Category.name == payload.name)
        .where(Category.tenant_id == tenant_id)
    )
    if exists:
        raise HTTPException(status_code=409, detail="Categoria ja existe")

    c = Category(name=payload.name, tenant_id=tenant_id)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c

@router.get("", response_model=list[CategoryOut])
def list_categories(
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    return list(
        db.scalars(
            select(Category)
            .where(Category.tenant_id == tenant_id)
            .order_by(Category.id)
        )
    )
