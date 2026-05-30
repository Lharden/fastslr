---
tags: [fastslr, algoritmo, pipeline]
---

# 🧪 Algoritmo - Pipeline de Triagem

Visão de ponta a ponta do que acontece **por artigo** dentro de `process_articles` (`engine.py`).

```
                 ┌────────────────────┐
   artigo ─────► │  T0 (pré-triagem)  │
                 └─────────┬──────────┘
                  REJECTED │ PASSED/FLAGGED
        ┌─────────────────┘
        ▼ (T0 REJECTED)              ▼ (segue)
  blocos = NOT_EVALUATED      ┌──────────────────────┐
                              │  para cada bloco:     │
                              │   evaluate_block()    │◄── fail-fast
                              │   APPROVED/FLAGGED/   │    (REJECTED pula
                              │   REJECTED            │     os próximos)
                              └──────────┬───────────┘
                                         ▼
                              ┌──────────────────────┐
                              │  make_final_decision  │
                              │  (special/strict/     │
                              │   k_of_n)             │
                              └──────────┬───────────┘
                                         ▼
                       APPROVED_FINAL / FLAGGED_FINAL / REJECTED_FINAL
```

## Os 3 estágios

### Estágio 1 — [[Algoritmo - Pré-triagem T0|T0 (pré-triagem global)]]
Filtro rápido por anti-termos globais (ex.: "book review", "editorial"). Se `REJECTED`, **nenhum bloco é avaliado** (todos viram `NOT_EVALUATED`) e a decisão final já é `REJECTED_FINAL`.

### Estágio 2 — [[Algoritmo - Avaliação de Bloco|Avaliação dos blocos de domínio]]
Cada bloco (CTX, TECH, …) é avaliado independentemente:
1. Busca termos positivos → níveis encontrados (`find_positive_terms`)
2. Busca anti-exclusão e anti-flag (`find_anti_terms`)
3. Calcula [[Algoritmo - Pontuação (Scoring)|score por seção]] (com uplift e cap)
4. Aplica [[Algoritmo - Avaliação de Bloco#Filtros de ruído|filtros de ruído]] (se `NOISE_PROFILE != relaxed`)
5. Decide `APPROVED`/`FLAGGED`/`REJECTED` por threshold do melhor nível

**Fail-fast** (`FAIL_FAST_GLOBAL`): se um bloco dá `REJECTED`, os blocos seguintes não são avaliados (otimização sem alterar o resultado na política `special`).

### Estágio 3 — [[Algoritmo - Decisão Final|Decisão final]]
`make_final_decision` combina os status dos blocos + T0 conforme a [[Algoritmo - Políticas de Decisão|política]] (`special` por padrão).

## Tratamento de erros e robustez

- Cada artigo roda dentro de um `try/except`. Sob `ERROR_POLICY=flag`, um erro vira um artigo `FLAGGED_FINAL` com a mensagem; sob `fail`, a run aborta.
- Após o loop, se a **taxa de erro** exceder `MAX_ERROR_RATE` (padrão 5%), a run inteira é abortada com `RuntimeError`.

## Determinismo

O pipeline é totalmente determinístico **exceto** por `run_timestamp` (`datetime.now()`), que é metadado e não afeta decisões. `sample_articles` (usado só no `preview`) aceita `seed` para amostragem reproduzível.

## Calibração (workflow recomendado)

`doctor` → `preview` (amostra) → `coverage` (remover dead/broad terms) → ajustar termos/thresholds → `run` → revisar `FLAGGED_FINAL` manualmente → `diff` entre iterações.

---

Relacionado: [[Algoritmo - Pré-triagem T0]] · [[Algoritmo - Avaliação de Bloco]] · [[Algoritmo - Decisão Final]] · [[Home]]
