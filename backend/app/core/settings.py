from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AliasChoices, model_validator

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
    AUTH_USERNAME: str = Field(default="", validation_alias=AliasChoices("IA_CNPJ_AUTH_USERNAME","AUTH_USERNAME"))
    # Prefira usar AUTH_PASSWORD_HASH em prod. AUTH_PASSWORD é fallback (lab/dev).
    AUTH_PASSWORD: str = Field(default="", validation_alias=AliasChoices("IA_CNPJ_AUTH_PASSWORD","AUTH_PASSWORD"))
    AUTH_PASSWORD_HASH: str = Field(default="", validation_alias=AliasChoices("IA_CNPJ_AUTH_PASSWORD_HASH","AUTH_PASSWORD_HASH"))
    AUTH_JWT_SECRET: str = Field(default="", validation_alias=AliasChoices("IA_CNPJ_AUTH_JWT_SECRET","AUTH_JWT_SECRET","AUTH_SECRET","JWT_SECRET"))
    AUTH_JWT_EXPIRE_MINUTES: int = Field(default=60, validation_alias=AliasChoices("IA_CNPJ_AUTH_JWT_EXPIRE_MINUTES","AUTH_JWT_EXPIRE_MINUTES","AUTH_TOKEN_EXPIRE_MINUTES"))
    BUILD_SHA: str = Field(default="", validation_alias=AliasChoices("IA_CNPJ_BUILD_SHA","BUILD_SHA","GITHUB_SHA"))

    @model_validator(mode="after")
    def _security_invariants(self):
        # Fail-fast de segurança (contrato de settings)
        if self.AUTH_PROTECT_DOCS and not self.AUTH_ENABLED:
            raise ValueError("SECURITY: AUTH_PROTECT_DOCS exige AUTH_ENABLED=true")

        if self.ENV == "prod" and not self.AUTH_ENABLED:
            raise ValueError("SECURITY: ENV=prod requer AUTH_ENABLED=true (failsafe)")

        if self.AUTH_ENABLED:

            user = (self.AUTH_USERNAME or '').strip()

            if not user:

                raise ValueError('SECURITY: AUTH_USERNAME vazio (obrigatório quando AUTH_ENABLED=true)')

            self.AUTH_USERNAME = user

            ph = str(self.AUTH_PASSWORD_HASH or '').strip()

            plain = str(self.AUTH_PASSWORD or '')

            if not ph and not plain:

                raise ValueError('SECURITY: AUTH_PASSWORD ou AUTH_PASSWORD_HASH obrigatório quando AUTH_ENABLED=true')

            if ph:

                try:

                    import passlib  # noqa: F401

                except Exception:

                    raise ValueError('SECURITY: AUTH_PASSWORD_HASH definido mas passlib não está disponível')

            self.AUTH_PASSWORD_HASH = ph

            sec = (self.AUTH_JWT_SECRET or "").strip()
            if not sec:
                raise ValueError("SECURITY: AUTH_JWT_SECRET vazio (obrigatório quando AUTH_ENABLED=true)")
            if len(sec) < 32:
                raise ValueError("SECURITY: AUTH_JWT_SECRET curto (min 32 chars)")
            # normaliza (remove espaços acidentais)
            self.AUTH_JWT_SECRET = sec

        return self
    AUTH_JWT_TTL_MIN: int = 60

settings = Settings()
