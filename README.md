# IA-CNPJ

Plataforma de consultoria financeira assistida por IA para **CNPJ e MEI**, com foco em **diagnóstico financeiro, categorização de lançamentos, relatórios e apoio operacional**.

O projeto foi separado do **Aurea Gold** para manter **estabilidade, compliance, governança e evolução organizada**.

---

## Visão do produto

O **IA-CNPJ** é um MVP técnico-comercial construído para ajudar empresas a organizar dados financeiros, categorizar movimentações, gerar análises e preparar terreno para consultoria assistida por IA.

Hoje o projeto já entrega uma base sólida de backend com:

- autenticação
- isolamento multi-tenant
- cadastro de empresas
- cadastro de categorias
- lançamentos financeiros
- relatórios
- fluxo de sugestão e aplicação de categorias
- esteira de CI com testes, smoke e contratos

---

## Público-alvo

- MEI
- pequenas empresas
- operações que precisam organizar lançamentos e relatórios
- consultorias financeiras que querem uma base SaaS para evolução futura

---

## O que o MVP já entrega

### Backend / API
- API em **FastAPI**
- autenticação por token
- suporte a multi-tenant
- isolamento de dados por tenant
- contratos validados por testes
- smoke tests para fluxo principal

### Domínio atual
- empresas
- categorias
- transações
- relatórios
- sugestões de categorização
- aplicação em lote de categorias

### Qualidade e governança
- CI com:
  - lint
  - settings contract
  - smoke
  - tests
- separação entre LAB e PROD
- fluxo protegido por pull request na branch `main`

---

## Estrutura do repositório

- `backend/` → API FastAPI, regras de negócio, integrações, testes e scripts
- `frontend/` → painel web em evolução
- `docs/` → governança, roadmap, decisões e escopo
- `scripts/` → automações auxiliares de desenvolvimento

---

## Estado atual do MVP

### Já validado
- auth multi-tenant em ambiente LAB
- contracts principais de companies
- contrato de `transactions.kind` padronizado em `in/out`
- relatórios por período
- data quality para transações sem categoria
- suggest/apply de categorias
- smoke CI-like com banco zerado
- CI verde com branch protection

### Em evolução
- painel frontend mais completo
- experiência de onboarding do produto
- empacotamento comercial do MVP
- expansão das rotinas de consultoria com IA

---

## Regras operacionais do projeto

1. **LAB ≠ PROD**  
   Nada quebra o ambiente estável.

2. **Um comando por vez**  
   Primeiro validação determinística, depois interface.

3. **Mudança relevante passa por teste e PR**  
   A branch `main` é protegida.

---

## Contratos importantes

### `transactions.kind`
O contrato oficial de transações aceita apenas:

- `in` → entrada
- `out` → saída

Valores como `income` e `expense` **não fazem parte do contrato atual** e devem ser rejeitados.

---

## Como rodar localmente

### Pré-requisitos
- Python 3.12+
- ambiente virtual `.venv`
- `curl`
- `jq`

### Rodando backend
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8110