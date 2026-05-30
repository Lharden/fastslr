---
tags: [fastslr, algoritmo, t0]
---

# 🚧 Algoritmo - Pré-triagem T0

T0 é o **filtro global** aplicado **antes** dos blocos de domínio. Serve para descartar rapidamente artigos obviamente fora de escopo (ex.: "book review", "editorial", "conference abstract").

Implementação: `evaluate_t0_conditional()` em `scoring.py`. Configuração: termos com bloco `GLOBAL` no `terms.csv` (convertidos para o bloco interno `T0` por `config.py`).

## Lógica

T0 usa **apenas anti-termos** (não tem positivos nem score):

```
anti_exclude encontrado?  → status = REJECTED  (escopo global)
senão anti_flag encontrado? → status = FLAGGED
senão                       → status = PASSED
```

Retorna `None` se nenhum bloco T0 estiver configurado (T0 é opcional).

## Efeito no pipeline

| Status T0 | Efeito |
|---|---|
| `REJECTED` | **Curto-circuito total**: todos os blocos viram `NOT_EVALUATED` e a decisão final é `REJECTED_FINAL` (T0 sobrepõe tudo). |
| `FLAGGED` | Blocos são avaliados normalmente, mas a decisão final será no mínimo `FLAGGED_FINAL` (passo 2 de `make_final_decision`). |
| `PASSED` | Sem efeito; segue para os blocos. |

Em `engine.py`, a variável `t0_prevents_evaluation = eval_t0 and eval_t0.status == "REJECTED"` controla esse curto-circuito.

## Tipos de termo T0

```csv
GLOBAL;anti;book review;;any;0;;      # → exclusão global (REJECTED)
GLOBAL;flag;editorial;;any;0;;        # → sinalização global (FLAGGED)
```

## Saída

Quando T0 existe, o resultado inclui `Status_T0`, `Reason_T0`, `Scope_T0`, `AntiHighlights_T0` e `Flags_T0`.

> [!note] Por que T0 importa para performance
> Excluir artigos fora de escopo logo no início evita avaliar todos os blocos para milhares de artigos irrelevantes — em conjunto com o **fail-fast** dos blocos.

---

Relacionado: [[Algoritmo - Pipeline de Triagem]] · [[Algoritmo - Decisão Final]] · [[Algoritmo - Avaliação de Bloco]] · [[Home]]
