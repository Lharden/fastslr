---
tags: [fastslr, validacao, testes]
---

# 🧪 Validação - Estratégia de Testes

Mapa da suíte de testes (`tests/`) e da sua relação com os [[Validação - Bugs e Riscos Conhecidos|findings]].

> [!important] Suspeitas ≠ bugs confirmados
> Os itens em [[Validação - Bugs e Riscos Conhecidos]] vieram de **revisão estática**. Vários já têm **teste de regressão** e podem estar mitigados. **Confirme rodando os testes antes de "corrigir"** — não assuma que a suspeita é real.

## Arquivos de teste

| Arquivo | Cobre |
|---|---|
| `test_engine.py` | `process_articles`, `collect_statistics`, config hash |
| `test_patterns.py` | compile_pattern, proximidade, detect_compound, precompile |
| `test_normalization.py` | NormalizationEngine, extract_normalization_rules |
| `test_config_regressions.py` | dedup, preservação por scope/level/is_regex, merge de blocos inline+CSV |
| `test_main_findings_regressions.py` | regressões de findings (abreviação, k_of_n, separador, coverage, diff…) |
| `test_compliance.py` | protocol.json (gerar/validar/migrar v2.0→v2.1), pacote ZIP, dedup de anexos |
| `conftest.py` | fixtures compartilhadas |

## Findings que JÁ têm teste de regressão (verificar antes de mexer)

| Finding | Teste relacionado | Implicação |
|---|---|---|
| #8 separador de CSV | `test_load_table_safe_prefers_separator_with_known_headers` | O código **prefere** o separador com headers conhecidos → a suspeita pode ser **falso alarme**; confirmar. |
| #15 broad-term | `test_coverage_broad_terms_count_articles_not_section_hits` | Conta artigos, não hits por seção → comportamento testado. |
| #4 normalização (abreviação) | `test_normalized_abbreviation_term_matches_normalized_article_text` | Matching de abreviação normalizada testado; o risco específico é `c++`/símbolos, **não** abreviações. |
| #7 export csv | `test_export_results_uses_csv_extension_when_only_csv_enabled` | Extensão por flag testada; confirmar o **default** quando `output` ausente. |
| k_of_n / fail-fast | `test_k_of_n_rejects_when_any_block_is_rejected_under_fail_fast_policy` | [[Algoritmo - Políticas de Decisão\|Política]] testada. |
| sem blocos | `test_no_domain_blocks_is_rejected_by_engine_and_validation` | Edge case coberto. |
| termos xlsx | `test_load_table_safe_accepts_xlsx_terms` | Carga XLSX coberta. |
| dedup/scope/level | `test_config_regressions.py` (8 testes) | Parsing de termos bem coberto. |

## Lacunas de teste sugeridas (para os findings em aberto)

- [ ] **#1** Teste de consistência: os 3 conjuntos de thresholds (`constants` / `presets` / `default_config`) devem ser iguais.
- [ ] **#2** Cobertura com termo contendo `"` (aspa dupla) → contagem correta.
- [ ] **#3** Termo com normalização que casa **não** deve aparecer como dead term.
- [ ] **#4** `symbol_replacement` para `c++`, `c#` → substituição efetiva.
- [ ] **#5** Wildcard `data*` deve (ou não — decidir) casar `data-driven`.
- [ ] **#6** Proximidade com `max_gap=0` e termos com 3 separadores.
- [ ] **#9** `run` com `--terms` inexistente → erro amigável (não traceback).
- [ ] **#10/#11** `diff` com IDs presentes só em um lado → "MISSING".
- [ ] **Determinismo**: rodar a mesma entrada 2× e comparar DataFrames (exceto `run_timestamp`).

## Comandos

```bash
pytest -q                 # suíte completa
pytest tests/test_scoring.py -q   # (criar — scoring não tem arquivo dedicado!)
ruff format . && ruff check .
pyright
```

> [!note] Gap notável
> Não há `test_scoring.py` dedicado. `scoring.py` é o **coração do algoritmo** ([[Algoritmo - Pontuação (Scoring)]], [[Algoritmo - Decisão Final]]) e merece testes unitários diretos de `evaluate_block`, `_compute_section_scores`, `make_final_decision` (incl. a regra especial) e dos filtros de ruído.

---

Relacionado: [[Validação - Checklist]] · [[Validação - Bugs e Riscos Conhecidos]] · [[Home]]
