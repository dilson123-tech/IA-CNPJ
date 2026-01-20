# IA-CNPJ — D11: IA Consultora CNPJ (versão “melhor do mercado”)

## Objetivo
Entregar uma “IA Consultora CNPJ” que:
1) melhora a categorização e sugere correções com qualidade,
2) explica o porquê (auditável),
3) nunca quebra o determinístico (fallback), e
4) é confiável (testes + smoke + CI).

## Princípios (não negociáveis)
- **Fallback obrigatório:** `AI_ENABLED=false` => sistema 100% determinístico.
- **Sem regressão:** CI + smoke sempre verdes.
- **Auditabilidade:** toda sugestão vem com **justificativa curta** + **confidence**.
- **Determinístico primeiro:** IA entra como “camada de sugestão”, não como chute cego.

## Entregas do D11 (checklist)
### 1) Contrato de resposta da IA (API)
- [ ] Definir um modelo padrão:
  - `suggested_category_id`
  - `confidence` (0.0–1.0)
  - `reason` (1–2 frases)
  - `signals` (lista curta: ex.: merchant match, keywords, amount pattern)
  - `provider` (rule-based/openai/...)
  - `dry_run` (true/false)

### 2) Endpoint “IA Consultora”
- [ ] Endpoint para sugerir categoria e explicar:
  - Entrada: `tx_id` (ou payload da transação)
  - Saída: modelo padrão acima
- [ ] Garantir `dry_run=true` não altera nada.
- [ ] `dry_run=false` aplica e registra auditoria.

### 3) Auditoria (rastro)
- [ ] Registrar sugestão/aplicação:
  - tx_id, categoria antes/depois, confidence, provider, reason, timestamp

### 4) Qualidade de dados (insights)
- [ ] Detectar transações “suspeitas”:
  - sem categoria, merchant vazio, valor fora de faixa, duplicidade simples
- [ ] Sugestão de ação (ex.: “revisar fornecedor”, “reclassificar”)

### 5) Testes “golden”
- [ ] Dataset pequeno com casos reais (10–30):
  - entradas + categoria esperada + reason mínima
- [ ] Rodar no CI (rápido) + smoke existente continua passando.

## Definition of Done (DoD)
- `bash backend/scripts/dev_up_smoke.sh` => **DEV UP + SMOKE PASS**
- `lint` e `smoke` verdes no GitHub Actions
- Endpoint IA Consultora funcionando com e sem IA (`AI_ENABLED` on/off)
- Auditoria gerada quando `dry_run=false`
