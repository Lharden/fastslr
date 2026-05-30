---
tags: [fastslr, reprodutibilidade, academico]
---

# 📦 Reprodutibilidade e Pacote Acadêmico

A reprodutibilidade é o motivo de existir do FastSLR (ver [[Objetivo e Visão]]). Ela é garantida por **determinismo do algoritmo** + **hashes verificáveis** + **snapshot do protocolo**.

## Garantia de reprodutibilidade

> Qualquer pessoa com os mesmos `artigos.csv`, `config.json`, `terms.csv` e a **mesma versão** do FastSLR produz **exatamente** os mesmos resultados.

Como:
1. Algoritmo 100% determinístico (regex sobre texto normalizado — sem ML).
2. `protocol.json` com hashes **SHA-256** das entradas.
3. Versão registrada (`triage_version`) em cada linha de saída.

## `academic_package.zip`

Gerado por `io.py` quando `output.academic_package = true`. Contém:

| Arquivo | Propósito |
|---|---|
| `triage_results.xlsx` | Resultados completos (scores, status, highlights) |
| `protocol.json` | Protocolo com hashes de entrada/config/execução (schema v2.1) |
| `triage_report.txt` | Relatório estatístico |
| `academic_report.md` | Relatório formatado para publicação |
| `config_audit.json` | Config completa utilizada |
| `APPENDIX_INDEX.md` | Índice dos artefatos |
| `appendix_manifest.json` | Manifesto de conformidade |

## `protocol.json`

Snapshot que permite verificar que nada foi alterado: hashes SHA-256 de input, terms e config, `execution_id`, timestamp e a versão. Deve ser incluído como **material suplementar** na publicação.

## Colunas de saída relevantes para auditoria

- `Title_Highlighted` / `Abstract_Highlighted` / `Tags_Highlighted` — termos casados marcados com `***termo***`
- `Highlights_<BLOCO>` / `AntiHighlights_<BLOCO>` / `Flags_<BLOCO>` — detalhes dos matches
- `Decision_Reason` — explicação textual de cada decisão
- `triage_version`, `run_timestamp`

## Relação com o protocolo RSL

O `docs/rsl/PROTOCOL.md` documenta o protocolo metodológico. O software implementa a fase de **screening** desse protocolo de forma auditável; o `protocol.json` é a evidência computacional dessa fase.

> [!bug] Riscos que afetam a reprodutibilidade/auditoria
> - Parsing frágil de highlights na **cobertura** (quebra com aspas no termo) e possível **falso-positivo de dead term** — itens #2/#3 em [[Validação - Bugs e Riscos Conhecidos]].
> - Highlight força `.upper()` no trecho casado (perde o case original).

---

Relacionado: [[Objetivo e Visão]] · [[Fluxo de Dados]] · [[Configuração - config e termos]] · [[Home]]
