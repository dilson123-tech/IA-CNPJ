from pydantic import BaseModel, Field, ConfigDict

class CategoryCreate(BaseModel):
    name: str = Field(min_length=1)

class CategoryOut(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)
