# ROADMAP — IA-CNPJ

## Código de Contexto (usar em TODO chat novo)
[PROJETO: IA-CNPJ]
[DOC: ROADMAP ATUAL]
[FOCO: MVP técnico-comercial + engine de inteligência]
[STATUS: Núcleo forte / acabamento de produto em evolução]

## Objetivo do Produto
O IA-CNPJ é o motor de inteligência e gestão financeira/fiscal para MEI/CNPJ, com foco em:
- organização de entradas e saídas
- categorização financeira
- relatórios e resumos executivos
- sugestões e aplicação assistida por IA
- apoio à tomada de decisão
- base técnica pronta para integração com camada SaaS externa

## Arquitetura definida
- IA-CNPJ = engine/API de inteligência
- ia-cnpj-saas = camada SaaS/orquestração/auth própria
- integração entre os dois via HTTP
- não copiar lógica de análise do engine para o SaaS

## Estado atual do produto
O projeto já possui, em nível relevante de maturidade:
- autenticação funcional
- rotas versionadas `/api/v1/*`
- multi-tenant com isolamento de dados
- gestão de empresas, categorias e transações
- relatórios e aliases versionados
- fluxo de IA consultiva
- testes automatizados
- smoke e CI
- documentação base de MVP

## Prestação de contas — estado objetivo agora
- Base técnica e operação: 97%
- Auth e segurança: 97%
- Multi-tenant e isolamento: 98%
- Domínio financeiro e relatórios: 96%
- IA e categorização: 95%
- Testes automatizados e smoke: 95%
- CI/CD e governança: 95%
- Frontend e onboarding: 72%
- Prontidão para mercado aberto: 86%
- Prontidão total real: 92%

## O que ainda segura o 100%
- frontend mais completo
- onboarding do produto
- empacotamento comercial do MVP
- expansão das rotinas de consultoria com IA
- roadmap público e documentação operacional mais alinhados ao estado atual

## Fases macro atuais
### Fase 1 — Núcleo backend e governança
Concluído em grande parte:
- auth
- entidades centrais
- contratos de API
- lint/smoke/CI
- governança básica

### Fase 2 — Motor financeiro e relatórios
Concluído em grande parte:
- empresas
- categorias
- transações
- relatórios
- resumos
- contratos versionados

### Fase 3 — IA consultiva
Concluído em boa parte:
- consultas de IA
- sugestão/aplicação de categorização
- respostas estruturadas
- melhorias recentes de contrato e compatibilidade

### Fase 4 — Blindagem de produto
Em evolução:
- testes adicionais
- documentação operacional
- ajustes de prontidão
- acabamento de integrações

### Fase 5 — Produto comercial
Em evolução:
- frontend mais forte
- onboarding
- posicionamento comercial
- fluxo de uso mais completo
- embalagem de MVP vendável

## Backlog estratégico
- Open Finance / CSV
- exportação PDF e canais externos
- multi-empresa mais avançado
- dashboards mais ricos
- expansão da consultoria IA
- mais recursos de operação comercial

## Checkpoints relevantes recentes
### 2026-03-10 a 2026-03-12 — Consolidação do MVP técnico
Entregas já refletidas no repositório:
- correção de contrato em transações (`in` / `out`)
- isolamento multi-tenant em entidades centrais
- aliases versionados para rotas relevantes
- testes cobrindo aliases e contratos
- correção do `category_name` em `recent_transactions`
- README reposicionado como MVP

### Checkpoint permanente
Sempre que houver fechamento relevante:
- atualizar esta régua percentual
- registrar o que foi concluído
- listar o que ainda impede 100%
- incluir essa leitura no handoff de troca de chat

