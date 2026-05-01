from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AliasChoices, model_validator

class Settings(BaseSettings):
    @staticmethod
    def _normalize_database_url(value: str) -> str:
        raw = str(value or '').strip()
        if not raw:
            return raw

        if raw.startswith('postgresql+psycopg://'):
            return raw

        if raw.startswith('postgres://'):
            return 'postgresql+psycopg://' + raw[len('postgres://'):]

        if raw.startswith('postgresql://'):
            return 'postgresql+psycopg://' + raw[len('postgresql://'):]

        return raw

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


    # IA (Facade / Providers)
    AI_ENABLED: bool = False
    AI_PROVIDER: str = "null"
    # OpenAI (provider real - ainda OFF por padrão)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_TIMEOUT_S: int = 25

    CNPJ_LOOKUP_PROVIDER: str = "brasilapi"
    CNPJ_LOOKUP_BASE_URL: str = "https://brasilapi.com.br/api/cnpj/v1"
    CNPJ_LOOKUP_TIMEOUT_S: int = 12

    ASAAS_ENABLED: bool = Field(default=False, validation_alias=AliasChoices("IA_CNPJ_ASAAS_ENABLED","ASAAS_ENABLED"))
    ASAAS_API_KEY: str = Field(default="", validation_alias=AliasChoices("IA_CNPJ_ASAAS_API_KEY","ASAAS_API_KEY"))
    ASAAS_BASE_URL: str = Field(default="https://api.asaas.com/v3", validation_alias=AliasChoices("IA_CNPJ_ASAAS_BASE_URL","ASAAS_BASE_URL"))
    ASAAS_WEBHOOK_TOKEN: str = Field(default="", validation_alias=AliasChoices("IA_CNPJ_ASAAS_WEBHOOK_TOKEN","ASAAS_WEBHOOK_TOKEN"))
    ASAAS_TIMEOUT_S: int = Field(default=20, validation_alias=AliasChoices("IA_CNPJ_ASAAS_TIMEOUT_S","ASAAS_TIMEOUT_S"))

    MERCADOPAGO_ENABLED: bool = Field(default=False, validation_alias=AliasChoices("IA_CNPJ_MERCADOPAGO_ENABLED","MERCADOPAGO_ENABLED"))
    MERCADOPAGO_ACCESS_TOKEN: str = Field(default="", validation_alias=AliasChoices("IA_CNPJ_MERCADOPAGO_ACCESS_TOKEN","MERCADOPAGO_ACCESS_TOKEN"))
    MERCADOPAGO_BASE_URL: str = Field(default="https://api.mercadopago.com", validation_alias=AliasChoices("IA_CNPJ_MERCADOPAGO_BASE_URL","MERCADOPAGO_BASE_URL"))
    MERCADOPAGO_WEBHOOK_SECRET: str = Field(default="", validation_alias=AliasChoices("IA_CNPJ_MERCADOPAGO_WEBHOOK_SECRET","MERCADOPAGO_WEBHOOK_SECRET"))
    MERCADOPAGO_TIMEOUT_S: int = Field(default=20, validation_alias=AliasChoices("IA_CNPJ_MERCADOPAGO_TIMEOUT_S","MERCADOPAGO_TIMEOUT_S"))

    PAGBANK_ENABLED: bool = Field(default=False, validation_alias=AliasChoices("IA_CNPJ_PAGBANK_ENABLED","PAGBANK_ENABLED"))
    PAGBANK_TOKEN: str = Field(default="", validation_alias=AliasChoices("IA_CNPJ_PAGBANK_TOKEN","PAGBANK_TOKEN"))
    PAGBANK_BASE_URL: str = Field(default="https://sandbox.api.pagseguro.com", validation_alias=AliasChoices("IA_CNPJ_PAGBANK_BASE_URL","PAGBANK_BASE_URL"))
    PAGBANK_WEBHOOK_URL: str = Field(default="", validation_alias=AliasChoices("IA_CNPJ_PAGBANK_WEBHOOK_URL","PAGBANK_WEBHOOK_URL"))

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
    ONBOARDING_ADMIN_EMAILS: str = Field(default="", validation_alias=AliasChoices("IA_CNPJ_ONBOARDING_ADMIN_EMAILS","ONBOARDING_ADMIN_EMAILS"))

    @model_validator(mode="after")
    def _security_invariants(self):
        self.DATABASE_URL = self._normalize_database_url(self.DATABASE_URL)
        # Fail-fast de segurança (contrato de settings)
        if self.AUTH_PROTECT_DOCS and not self.AUTH_ENABLED:
            raise ValueError("SECURITY: AUTH_PROTECT_DOCS exige AUTH_ENABLED=true")

        if self.ENV == "prod" and not self.AUTH_ENABLED:
            raise ValueError("SECURITY: ENV=prod requer AUTH_ENABLED=true (failsafe)")

        if self.ASAAS_ENABLED:
            if not str(self.ASAAS_API_KEY or "").strip():
                raise ValueError("SECURITY: ASAAS_API_KEY obrigatório quando ASAAS_ENABLED=true")
            if not str(self.ASAAS_BASE_URL or "").strip():
                raise ValueError("SECURITY: ASAAS_BASE_URL obrigatório quando ASAAS_ENABLED=true")

        if self.MERCADOPAGO_ENABLED:
            if not str(self.MERCADOPAGO_ACCESS_TOKEN or "").strip():
                raise ValueError("SECURITY: MERCADOPAGO_ACCESS_TOKEN obrigatório quando MERCADOPAGO_ENABLED=true")
            if not str(self.MERCADOPAGO_BASE_URL or "").strip():
                raise ValueError("SECURITY: MERCADOPAGO_BASE_URL obrigatório quando MERCADOPAGO_ENABLED=true")

        if self.PAGBANK_ENABLED:
            if not str(self.PAGBANK_TOKEN or "").strip():
                raise ValueError("SECURITY: PAGBANK_TOKEN obrigatório quando PAGBANK_ENABLED=true")
            if not str(self.PAGBANK_BASE_URL or "").strip():
                raise ValueError("SECURITY: PAGBANK_BASE_URL obrigatório quando PAGBANK_ENABLED=true")
            if not str(self.PAGBANK_WEBHOOK_URL or "").strip():
                raise ValueError("SECURITY: PAGBANK_WEBHOOK_URL obrigatório quando PAGBANK_ENABLED=true")

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
