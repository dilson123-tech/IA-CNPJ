from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AliasChoices

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


    # IA (Facade / Providers)
    AI_ENABLED: bool = False
    AI_PROVIDER: str = "null"
    # OpenAI (provider real - ainda OFF por padrão)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_TIMEOUT_S: int = 25

    APP_NAME: str = "IA-CNPJ API"
    ENV: str = Field(default="lab", validation_alias=AliasChoices("IA_CNPJ_ENV","ENV"))  # lab|prod
    DATABASE_URL: str = Field(default="sqlite:///./lab.db", validation_alias=AliasChoices("IA_CNPJ_DATABASE_URL","DATABASE_URL"))
    # Auth (JWT)
    AUTH_ENABLED: bool = Field(default=False, validation_alias=AliasChoices("IA_CNPJ_AUTH_ENABLED","AUTH_ENABLED"))
    AUTH_PROTECT_DOCS: bool = Field(default=False, validation_alias=AliasChoices("IA_CNPJ_AUTH_PROTECT_DOCS","AUTH_PROTECT_DOCS"))
    AUTH_USERNAME: str = ""
    # Prefira usar AUTH_PASSWORD_HASH em prod. AUTH_PASSWORD é fallback (lab/dev).
    AUTH_PASSWORD: str = ""
    AUTH_PASSWORD_HASH: str = ""
    AUTH_JWT_SECRET: str = ""
    AUTH_JWT_TTL_MIN: int = 60

settings = Settings()
