# IA-CNPJ (Consultoria Financeira com IA)

Produto robusto (comercial) focado em CNPJ/MEI: diagnóstico financeiro, alertas, relatórios e consultoria assistida por IA.
Este repositório é separado do Aurea Gold para manter estabilidade, compliance e evolução organizada.

## Estrutura
- backend/  -> API (FastAPI) + regras/serviços + integrações
- frontend/ -> Painel web (futuro: app)
- docs/     -> governança (roadmap, decisões, escopo)
- scripts/  -> automações de dev

## Regras (anti-bagunça)
1. Mudanças seguem o PDF Diário (8h). Ideias fora disso entram no Backlog.
2. Um comando por vez + testes determinísticos (curl) antes de UI.
3. LAB ≠ PROD. Nada quebra o estável.
