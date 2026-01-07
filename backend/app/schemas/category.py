from pydantic import BaseModel, Field

class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)

class CategoryOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True
