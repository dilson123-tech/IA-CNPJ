from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.deps import get_db
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryOut

router = APIRouter(prefix="/categories", tags=["categories"])

@router.post("", response_model=CategoryOut)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    exists = db.scalar(select(Category).where(Category.name == payload.name))
    if exists:
        raise HTTPException(status_code=409, detail="Categoria ja existe")
    c = Category(name=payload.name)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c

@router.get("", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return list(db.scalars(select(Category).order_by(Category.id)))
