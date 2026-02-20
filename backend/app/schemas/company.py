from pydantic import BaseModel, Field, ConfigDict


class CompanyCreate(BaseModel):
    cnpj: str = Field(min_length=14, max_length=14)
    razao_social: str


class CompanyOut(BaseModel):
    id: int
    cnpj: str
    razao_social: str

    model_config = ConfigDict(from_attributes=True)
