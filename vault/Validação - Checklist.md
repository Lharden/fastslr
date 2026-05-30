---
tags: [fastslr, validacao, checklist]
---

# ✅ Validação - Checklist

Checklist mestre para garantir que a triagem está **correta, reproduzível e robusta** antes de entregar ao usuário final. Marque os itens conforme forem verificados/corrigidos.

> Detalhes técnicos de cada bug em [[Validação - Bugs e Riscos Conhecidos]]. Cobertura de testes em [[Validação - Estratégia de Testes]].

> [!success] Status — Fase 0–5 concluída (commit `fe46012`)
> Os 46 findings da [[Validação - Auditoria Completa]] foram corrigidos com TDD. Estado verificado: **218 testes** · `ruff check`/`format` limpos · **`pyright` 0 erros** · determinismo reconfirmado. Detalhes em [[Validação - Correções Aplicadas]].
> Itens abaixo marcados refletem o que a auditoria expandiu/confirmou (a numeração #1–#15 original mapeia para os findings detalhados da auditoria).

## 🔥 Correções de lógica prioritárias (Alta)

- [x] **#1** Unificar thresholds de flag (constants vs presets vs default_config) numa única fonte de verdade + teste de consistência → `test_thresholds_consistencia.py`
- [x] **#2** Substituir parsing frágil de highlights na cobertura (escape robusto via `json`) + teste com termo contendo aspas → `test_coverage_quotes.py`
- [x] **#3** Corrigir falso-positivo de "dead term" → coberto pelo fix de serialização de highlights (#2)

## 🟧 Correções de matching/UX (Média)

- [x] **#4** Heurística de símbolo na normalização (`c++`, `c#`, `.NET`) + boundaries condicionais + ordem determinística → `test_boundaries.py`, `test_normalization_determinism.py`
- [x] **#5** Wildcard/boundary cobrindo termos com char não-word (C++, C#, .NET, F#) → `test_boundaries.py`
- [x] **#6** Semântica de gap de proximidade (clamp ≥0, separador ampliado, split recursivo) → `test_proximity.py`
- [x] **#7** Alinhar default de export `csv` (código vs JSON) → `test_io_coverage_extra.py`
- [x] **#8** Detecção de separador/encoding de CSV robustecida (fallback determinístico) → `test_io_encoding.py`
- [x] **#9** `run`/`preview`/`coverage`/`diff` validam arquivos ausentes com mensagem amigável → `test_cli.py`
- [x] **#10** `diff` marca "MISSING" corretamente (`fillna`) + teste de ID em um só lado → `test_main_findings_regressions.py`
- [x] **#11** `diff` valida coluna de ID em ambos os arquivos antes do merge → `test_main_findings_regressions.py`

## 🟨 Robustez/cosmético (Baixa)

- [x] **#12** `new-project` não sobrescreve projeto existente sem `--force` → `test_main_findings_regressions.py`
- [x] **#13** `_()` captura/loga falha de `.format` (inclui `ValueError`)
- [x] **#14** Highlight: serialização robusta (`json`) — `.upper()` confirmado intencional (refutado na auditoria)
- [x] **#15** Itens menores: tipagem `int(idx)`, condicionais pandas, piso de corpus em broad-term, `getlocale()`, sanitização de perfil, etc.

> [!note] Pendências conscientes (não aplicadas, sem impacto nos gates)
> Dead code em `adapters.py`/`export_raw_subset`; papel do `default_config.json` (cosmético/documental). Ver [[Validação - Correções Aplicadas]].

## 🧪 Validação funcional (rodar antes de release)

- [x] `pytest` — toda a suíte passa (`tests/`) → **218 passed**
- [x] `ruff format` + `ruff check` — zero erros
- [x] `pyright` (standard) — zero erros (0/0/0)
- [x] `fastslr doctor` em um dataset real → colunas/termos detectados corretamente
- [x] `fastslr run` em `data/Final_Corpus.csv` com `data/terms_final.csv` → executa e gera artefatos
- [x] Rodar a **mesma** entrada duas vezes → resultados **idênticos** (exceto `run_timestamp`) — determinismo confirmado
- [x] Conferir `protocol.json` entre execuções idênticas → só campos voláteis diferem
- [ ] `fastslr coverage` → revisar dead/broad terms (revisão manual de calibração — opcional)
- [x] `fastslr diff v1 v2` → transições corretas (#10/#11 resolvidos)

## 🧷 Casos-limite a verificar (edge cases)

- [ ] CSV só com headers (0 linhas) — ✅ já tratado (regressão #1 do stress test)
- [ ] Artigo sem abstract / sem tags (uplift aplicado?)
- [ ] Artigo sem nenhum termo positivo → `REJECTED` "No positive terms found"
- [ ] Termo com aspas duplas, com `*`, com `c++`/`c#`, regex inválida (`re.error` ignorada?)
- [ ] Encoding não-UTF8 / separador `,` vs `;` vs `\t`
- [ ] IDs duplicados ou numéricos (`1.0` vs `1`)
- [ ] Taxa de erro > `MAX_ERROR_RATE` → run aborta corretamente
- [ ] Política `strict` e `k_of_n` produzem resultados coerentes com a tabela em [[Algoritmo - Políticas de Decisão]]
- [ ] Regra especial: 1 bloco FLAGGED + demais APPROVED com score ≥ 40 → APPROVED_FINAL

## 📋 Pré-publicação acadêmica

- [ ] `protocol.json` gerado e válido (schema v2.1)
- [ ] `academic_package.zip` contém todos os 7 artefatos
- [ ] `config_hash` documentado na publicação
- [ ] Versão (`triage_version`) registrada e consistente

---

Relacionado: [[Validação - Bugs e Riscos Conhecidos]] · [[Validação - Estratégia de Testes]] · [[Home]]
