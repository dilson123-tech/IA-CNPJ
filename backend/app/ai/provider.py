from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence, Optional, List, Dict, Any


# -----------------------------
# Contract: AI Provider
# -----------------------------

@dataclass(frozen=True)
class SuggestInputItem:
    """
    Item mínimo que o provider recebe para sugerir categoria.
    Mantém o contrato independente do banco/ORM.
    """
    id: int
    description: str
    kind: str  # "in" | "out"
    amount_cents: int
    occurred_at: Optional[str] = None  # ISO string opcional


@dataclass(frozen=True)
class SuggestOutputItem:
    """
    Saída padronizada do provider.
    category_name é preferida (depois resolvemos p/ id).
    """
    id: int
    category_name: Optional[str] = None
    confidence: float = 0.0
    rule: str = "ai"
    notes: Optional[str] = None


class AISuggestCategoriesProvider(Protocol):
    def suggest_categories(
        self,
        company_id: int,
        items: Sequence[SuggestInputItem],
        *,
        include_no_match: bool = False,
    ) -> List[SuggestOutputItem]:
        """
        Retorna uma lista com sugestões por transação.
        - Se include_no_match=False: pode retornar somente as que tiverem category_name.
        - Se include_no_match=True: pode retornar também itens sem match (category_name=None).
        """
        ...


# -----------------------------
# Default provider: NULL (no-op)
# -----------------------------

class NullSuggestProvider:
    """
    Provider padrão (safe): não chama nada externo.
    A ideia é: AI_ENABLED=false => sempre cair no rule-based determinístico.
    """
    def suggest_categories(
        self,
        company_id: int,
        items: Sequence[SuggestInputItem],
        *,
        include_no_match: bool = False,
    ) -> List[SuggestOutputItem]:
        if include_no_match:
            return [
                SuggestOutputItem(id=i.id, category_name=None, confidence=0.0, rule="no_match")
                for i in items
            ]
        return []


def get_provider(name: str | None) -> AISuggestCategoriesProvider:
    """
    Factory simples. Hoje só null.
    Amanhã: 'openai', 'anthropic', etc.
    """
    n = (name or "null").strip().lower()
    if n in ("null", "noop", "none", ""):
        return NullSuggestProvider()
    # placeholder para próximos providers
    raise ValueError(f"Unknown AI provider: {n!r}")


# --- D08: config + switch (settings -> provider) ------------------------------

def get_ai_config():
    """Lê AI_ENABLED/AI_PROVIDER via pydantic-settings (preferencial) e cai para env como fallback."""
    try:
        import importlib
        mod = importlib.import_module("app.core.settings")
        s = None
        if hasattr(mod, "settings"):
            s = getattr(mod, "settings")
        elif hasattr(mod, "get_settings"):
            s = mod.get_settings()
        elif hasattr(mod, "Settings"):
            s = mod.Settings()
        enabled = bool(getattr(s, "AI_ENABLED", False))
        provider = str(getattr(s, "AI_PROVIDER", "null") or "null")
        return enabled, provider
    except Exception:
        import os
        v = (os.getenv("AI_ENABLED", "false") or "false").strip().lower()
        enabled = v in ("1", "true", "yes", "on")
        provider = (os.getenv("AI_PROVIDER", "null") or "null").strip()
        return enabled, provider

def get_active_provider():
    enabled, name = get_ai_config()
    if not enabled:
        return None
    return get_provider(name)

def provider_suggest_categories(req, include_no_match: bool = False):
    """Tenta provider quando AI_ENABLED=true. Se não houver provider aplicável, retorna None (caller faz fallback)."""
    prov = get_active_provider()
    if prov is None:
        return None

    import inspect
    for meth_name in ("suggest_categories", "suggest", "suggest_categories_for_transactions", "suggest_transaction_categories"):
        if hasattr(prov, meth_name):
            fn = getattr(prov, meth_name)
            try:
                sig = inspect.signature(fn)
                params = [p for p in sig.parameters.values()]
                argc = len(params)
                if argc <= 1:
                    return fn()
                if argc == 2:
                    return fn(req)
                if argc == 3:
                    return fn(req, include_no_match)
                kwargs = {}
                if "req" in sig.parameters: kwargs["req"] = req
                if "payload" in sig.parameters: kwargs["payload"] = req
                if "include_no_match" in sig.parameters: kwargs["include_no_match"] = include_no_match
                if kwargs:
                    return fn(**kwargs)
                return fn(req)
            except Exception:
                return None

    return None
