---
tags: [fastslr, validacao, correcoes]
---

# 🔧 Validação - Correções Aplicadas (Fase 0–5)

## Sumário

As **Fases 0 a 5 estão completas**. Foram aplicadas e validadas **18 grupos de findings** no total — 8 grupos nas Fases 0–3 e 10 grupos adicionais nas Fases 4–5 + Polimento Final —, todos com testes automatizados dedicados. A barreira de validação final passou com **status 100% verde em todas as quatro ferramentas**: `218 passed` no pytest, `ruff check` sem erros, `ruff format --check` limpo (42 arquivos formatados), `pyright` com 0 erros, e determinismo dos resultados de triagem reconfirmado.

Resumo por fase:

- **Fase 0 — Infra de Testes**: baseline de smoke tests da CLI (21 testes).
- **Fase 1 — Matching Core**: word-boundary anchoring + lógica de decisão de scoring.
- **Fase 2 — IO / Packaging**: encoding robusto, dados via `importlib.resources`, sanitização de perfis.
- **Fase 3 — CLI / UX**: erros amigáveis (sem tracebacks crus), correção de diff/new-project e highlights com aspas.
- **Fase 4–5 — Robustez de núcleo, CLI/i18n, IO/coverage, TUI, scoring, controller + Polimento Final**: 10 grupos de findings de severidade Média/Baixa, fechamento dos gates `ruff format` e `pyright`, e reconfirmação de determinismo.

Status da validação final: **PASSED** — pytest 100% verde, `ruff check` limpo, `ruff format --check` limpo e `pyright` com 0 erros (todos os quatro gates satisfeitos).

## Correções por fase

| Fase | Grupo | Arquivos alterados | Testes adicionados | Status |
|------|-------|--------------------|--------------------|--------|
| **Fase 0 — Infra de Testes** | CLI smoke tests (baseline Fase 2) | `tests/test_cli.py` | 21 testes (`test_version_happy`, `test_doctor_*`, `test_run_*`, `test_preview_happy`, `test_coverage_happy`, `test_diff_happy`, `test_new_project_*`, `test_export_*`, `test_terms_happy`, `test_profile_*`) | ✅ |
| **Fase 1 — Matching Core** | word-boundary anchoring | `src/fastslr/core/patterns.py`, `src/fastslr/core/normalization.py`, `tests/test_boundaries.py` | 9 testes (`TestConditionalBoundaries::test_cpp_matches_in_text`, `…test_csharp_matches_in_text`, `…test_dotnet_matches_isolated`, `…test_fsharp_matches_in_text`, `…test_dotnet_leading_edge_relaxed`, `…test_word_term_still_requires_boundary`, `…test_wildcard_still_works`, `TestSymbolReplacementBoundaries::test_csharp_and_cpp_symbol_replacement`, `…test_symbol_keys_lowercased_on_construction`) | ✅ |
| **Fase 1 — Matching Core** | scoring-decision-logic | `src/fastslr/core/scoring.py`, `src/fastslr/core/config.py`, `tests/test_scoring.py` | 9 testes (`test_single_flagged_block_alone_is_flagged_not_approved`, `test_special_rule_approves_when_others_approved_above_threshold`, `test_special_rule_does_not_apply_when_approved_below_threshold`, `test_all_blocks_approved_is_approved_final`, `test_zero_score_block_is_rejected_not_flagged`, `test_positive_score_at_flag_threshold_still_flags`, `test_evaluate_block_happy_path_approved`, `test_compute_section_scores_dedups_levels_and_weights`, `test_out_of_range_level_makes_block_rejected`) | ✅ |
| **Fase 2 — IO / Packaging** | io-encoding | `src/fastslr/core/io.py`, `tests/test_io_encoding.py` | 5 testes (`test_cp1252_csv_loads_without_chardet`, `test_latin1_csv_loads_without_chardet`, `test_utf8_sig_csv_loads`, `test_plain_utf8_csv_loads`, `test_configured_encoding_is_prioritized`) | ✅ |
| **Fase 2 — IO / Packaging** | packaging-data-importlib-resources | `pyproject.toml`, `src/fastslr/i18n/__init__.py`, `tests/test_packaging.py` | 8 testes (`test_locale_files_resolvable_via_importlib_resources[en/pt_BR/es]`, `test_core_default_config_resolvable_via_importlib_resources`, `test_py_typed_marker_present`, `test_translation_returns_text_not_key`, `test_translation_localized_pt_br`, `test_locale_loader_uses_importlib_resources`) | ✅ |
| **Fase 2 — IO / Packaging** | profiles-sanitization | `src/fastslr/app/profiles.py`, `tests/test_profiles.py` | 7 testes (`test_save_profile_confines_path_traversal`, `test_save_profile_rejects_empty_name`, `test_save_profile_rejects_name_with_only_separators`, `test_load_profile_confines_path_traversal`, `test_delete_profile_confines_path_traversal`, `test_round_trip_valid_name`, `test_sanitized_collision_maps_to_same_file`) | ✅ |
| **Fase 3 — CLI / UX** | cli-raw-tracebacks-and-false-warnings | `src/fastslr/app/cli.py`, `src/fastslr/__main__.py`, `src/fastslr/core/config.py`, `src/fastslr/i18n/locales/{en,pt_BR,es}.json`, `tests/test_cli.py` | 11 testes (`test_preview_missing_input_exits_1_friendly`, `test_preview_missing_config_exits_1_friendly`, `test_coverage_missing_input_exits_1_friendly`, `test_coverage_missing_terms_exits_1_friendly`, `test_diff_missing_file_exits_1_friendly`, `test_terms_missing_config_exits_1_friendly`, `test_terms_missing_terms_exits_1_friendly`, `test_profile_save_missing_config_exits_1_friendly`, `test_normalization_rows_do_not_warn_empty_kind`, `test_normalization_rows_still_parsed_as_rules`, `test_run_noninteractive_proceeds_past_warnings`) | ✅ |
| **Fase 3 — CLI / UX** | diff + new-project | `src/fastslr/app/controller.py`, `tests/test_main_findings_regressions.py` | 3 testes (`test_diff_exclusive_ids_report_missing_not_nan`, `test_diff_without_common_id_column_raises_friendly_valueerror`, `test_create_project_refuses_silent_overwrite`) | ✅ |
| **Fase 3 — CLI / UX** | highlight-quotes-deadterm | `src/fastslr/core/io.py`, `src/fastslr/core/coverage.py`, `tests/test_coverage_quotes.py` | 4 testes (`test_pack_highlights_roundtrip_recovers_term_with_quote`, `test_pack_highlights_roundtrip_plain_term`, `test_term_with_quote_not_reported_as_dead`, `test_multiple_highlights_with_quotes_in_one_cell`) | ✅ |

## Validação final

Comandos rodados via Bash (Windows) no repositório `C:\Users\Leonardo\Documents\projects\fastslr`. **Nenhum arquivo do repositório foi modificado durante a validação.**

| Verificação | Resultado | Conta para `passed`? |
|-------------|-----------|----------------------|
| `python -m pytest -q` | **144 passed, 1 warning** em 1.35s — 100% verde | ✅ Sim — satisfeito |
| `python -m ruff check .` | **All checks passed!** — zero erros | ✅ Sim — satisfeito |
| `python -m ruff format --check .` | ❌ exit 1 — 10 arquivos seriam reformatados (25 já formatados) | ⚠️ Não entra no critério |
| `python -m pyright` | 24 errors, 0 warnings | ⚠️ Não entra no critério |

**Status final: `passed = true`** (pytest 100% verde **E** `ruff check` sem erros — ambos critérios satisfeitos).

### Aviso do pytest (não-bloqueante)

- 1 `DeprecationWarning`: `locale.getdefaultlocale` em `src/fastslr/i18n/__init__.py:99`.

### Formatação (`ruff format --check`) — registrado, fora do critério

10 arquivos seriam reformatados: `src/fastslr/app/controller.py`, `app/tui.py`, `core/config.py`, `core/engine.py`, `core/io.py`; `tests/test_cli.py`, `test_engine.py`, `test_io_encoding.py`, `test_main_findings_regressions.py`, `test_scoring.py`.

### Pyright — 24 erros (fora do critério `passed`)

Três padrões recorrentes:

1. **`reportArgumentType` — `Hashable` não atribuível a `ConvertibleToInt`** em chamadas `int()` sobre índices pandas: `config.py:198 (x2)`, `config.py:205 (x2)`, `config.py:319 (x2)`, `config.py:339 (x2)`, `normalization.py:114 (x2)`, `normalization.py:122 (x2)`.
2. **`reportGeneralTypeIssues` — "Invalid conditional operand `bool|NDArray|NDFrame`"** (o `__bool__` de objetos pandas retorna `NoReturn`): `config.py:225`, `config.py:241`, `config.py:282`, `config.py:302`, `engine.py:222`, `engine.py:223`, `engine.py:224`.
3. **`reportMissingImports` — `chardet` não resolvido** (stub/pacote ausente no ambiente do pyright): `io.py:22`.

### Check de determinismo — ✅ OK

Triagem rodada 2x na mesma entrada (`data/Final_Corpus.csv`, config `src/fastslr/core/default_config.json`, terms `data/terms_final.csv`) para `%TEMP%\fastslr_det1` e `_det2`. Ambas com exit 0. Comparação ignorando timestamps:

- `triage_results.xlsx`: **TODAS as sheets idênticas** (dados de resultado iguais).
- `triage_report.txt`: **idêntico**.
- `config_audit.json`: **idêntico**.
- `protocol.json` e `academic_report.md`: diferem **apenas em metadados não-determinísticos por design** — `execution_id` aleatório (`run_8733ade4e985` vs `run_60969fe3f7fb`), `generated_at` (timestamp), `processing_time_seconds`/`articles_per_second` (métricas de wall-clock) e `results_path` (apenas porque o diretório de saída é det1 vs det2). **Nenhuma diferença nos dados de triagem.**

**Conclusão: determinismo dos resultados confirmado.** Diretórios temporários removidos; nenhum arquivo do repositório alterado.

## Fase 4–5 + Polimento Final

As correções de severidade **Média** e **Baixa** foram aplicadas em **10 grupos de findings**, cobrindo robustez de núcleo, CLI/i18n, IO/coverage, TUI, scoring e controller. Em seguida, um passo de **Polimento Final** fechou os gates de formatação (`ruff format`) e tipagem (`pyright`).

### Grupos aplicados (Fase 4–5)

| Grupo | Arquivos alterados | Testes adicionados | Findings resolvidos |
|-------|--------------------|--------------------|---------------------|
| **proximity-patterns** | `src/fastslr/core/patterns.py`, `tests/test_proximity.py` | `tests/test_proximity.py` (suíte de proximidade) | `proximity-negative-gap-literal-no-match`, `proximity-requires-adjacent-space`, `compound-splits-only-first-separator`, `proximity-token-unit-injection` |
| **normalization** | `src/fastslr/core/normalization.py`, `tests/test_normalization_determinism.py` | `test_overlapping_symbol_order_independent`, `test_symbol_value_is_lowercased`, `test_identical_symbol_rows_no_spurious_warning`, `test_symbol_key_case_collision_warns`, `test_lru_evicts_least_recently_used`, `test_cache_returns_consistent_result` | `rule-order-dependent-output`, `symbol-replacement-value-not-lowercased`, `dup-detection-symbol-case-asymmetry`, `lru-cache-on-n` |
| **config-robustez** | `src/fastslr/core/config.py`, `tests/test_config_robustez.py` | `test_csv_block_matches_block_order_case_insensitive`, `test_csv_block_whitespace_matches_block_order`, `test_csv_block_truly_absent_still_warns`, `test_required_columns_accept_titlecase_header`, `test_required_columns_accept_trailing_space_header`, `test_required_columns_error_lists_found_columns`, `test_max_gap_negative_is_clamped_to_zero`, `test_max_gap_positive_is_preserved` | `csv-block-case-sensitive-silent-ignore`, `required-columns-no-header-normalization`, `proximity-negative-gap-literal-no-match` (metade do clamp no config) |
| **constants-version-thresholds** | `src/fastslr/core/constants.py`, `tests/conftest.py`, `pyproject.toml`, `tests/test_thresholds_consistencia.py` | `test_flagging_threshold_l4_aligned_across_sources`, `test_flagging_thresholds_fully_consistent_across_sources`, `test_version_single_source_of_truth` | `flagging-threshold-l4-divergence`, `versao-duplicada-mao` |
| **engine-stats** | `src/fastslr/core/engine.py`, `tests/test_engine_stats.py` | `test_collect_statistics_reports_explicit_denominator_with_error_rows`, `test_process_articles_marks_error_rows_so_stats_denominator_is_coherent`, `test_id_output_collision_with_generated_column_raises_clear_error`, `test_id_output_collision_with_block_status_column_raises`, `test_default_id_output_does_not_collide` | `stats-inconsistent-denominator-error-rows`, `id-output-key-collision` |
| **cli-i18n** | `src/fastslr/app/cli.py`, `src/fastslr/i18n/__init__.py`, `src/fastslr/i18n/locales/{en,pt_BR,es}.json`, `tests/test_cli.py` | `test_preview_sample_zero_exits_1_friendly`, `test_preview_sample_negative_exits_1_friendly`, `test_preview_sample_zero_checked_before_files`, `test_doctor_localized_pt_br_no_english_headers`, `test_doctor_localized_pt_br_setup_errors`, `test_new_project_refuses_existing_without_force`, `test_new_project_force_overwrites_existing`, `test_i18n_format_valueerror_does_not_crash`, `test_detect_locale_env_var_priority`, `test_detect_locale_parses_lang_env`, `test_detect_locale_no_deprecation_warning` | `preview-sample-zero-silent-empty`, `doctor-not-localized-mixed-language`, `i18n-detect-locale-deprecated-getdefaultlocale`, `i18n-format-valueerror-uncaught` |
| **io-coverage** | `src/fastslr/core/io.py`, `src/fastslr/core/coverage.py`, `tests/test_io_coverage_extra.py` | `test_migrate_incomplete_v10_snapshot_produces_valid_snapshot`, `test_migrate_rejects_unknown_source_version`, `test_migrate_rejects_missing_source_version`, `test_migrate_complete_v20_snapshot_still_works`, `test_export_opts_default_matches_template`, `test_export_opts_explicit_output_block_still_honored`, `test_export_results_minimal_config_writes_xlsx_not_csv`, `test_broad_terms_not_flagged_for_tiny_corpus`, `test_broad_terms_flagged_for_large_corpus` | `migrate-protocol-snapshot-incompleto`, `default-config-csv-false-vs-codigo-true`, `broad-terms-strict-gt-corpus-pequeno` |
| **TUI (UX/robustez)** | `src/fastslr/app/tui.py`, `tests/test_tui_findings.py` | `tests/test_tui_findings.py` (suíte de findings da TUI) | `tui-worker-ui-access-from-thread`, `tui-settings-locale-empty-no-feedback`, `tui-settings-locale-not-applied-current-screen`, `tui-empty-input-silent-return`, `tui-results-detail-cursor-row-empty` |
| **scoring** | `src/fastslr/core/scoring.py`, `tests/test_scoring.py` | `test_non_numeric_level_is_ignored_not_crashing`, `test_numeric_string_level_is_coerced` | `find-positive-terms-int-level-crash` |
| **controller** | `src/fastslr/app/controller.py`, `tests/test_main_findings_regressions.py` | `test_run_triage_aborts_on_header_only_corpus`, `test_export_academic_package_rejects_table_without_final_decision`, `test_export_academic_package_accepts_valid_result`, `test_browse_terms_exposes_parse_warnings` | `empty-corpus-silent-success`, `export-academic-no-validation-empty-package`, `browse-terms-shows-precompiled-mismatch-note`, `create-project-silent-overwrite` |

**Total Fase 4–5**: **31 findings resolvidos** em 10 grupos.

### Polimento Final

Após os 10 grupos rodarem (alguns em paralelo), um agente de polimento normalizou o estado do repositório:

1. **`ruff format`** — `python -m ruff format .` reformatou 7 arquivos deixados sem formatar pelos agentes paralelos: `src/fastslr/app/controller.py`, `src/fastslr/core/io.py`, `tests/test_cli.py`, `tests/test_engine.py`, `tests/test_io_encoding.py`, `tests/test_main_findings_regressions.py`, `tests/test_scoring.py`. Apenas mudanças de whitespace; nenhuma regressão de teste.
2. **`pyright` — 12 erros eliminados via escopo correto.** Causa-raiz: os 12 erros estavam **exclusivamente** no artefato de build obsoleto e gitignorado `build/lib/fastslr/` (`config.py`, `engine.py`, `io.py`, `normalization.py`) — **não** no código-fonte real. `python -m pyright src` já estava com 0 erros; o pyright varria `build/` por padrão. Correção: escopar o pyright ao código real adicionando `include`/`exclude` em `[tool.pyright]` no `pyproject.toml`:
   - `include = ["src", "tests"]`
   - `exclude = ["build", "dist", "teste", "**/__pycache__", "**/.ruff_cache", "**/.pytest_cache"]`
   `build/` e `teste/` são ambos gitignorados e não devem ser type-checados. O erro de import faltante de `chardet` entre os 12 também era exclusivo do build; o import real em `src/fastslr/core/io.py` já é tratado no fonte.

Arquivos editados no polimento: apenas `pyproject.toml` (mais as mudanças whitespace-only do `ruff format` nos 7 arquivos acima). Nenhuma lógica de teste foi alterada — a suíte estava 100% verde imediatamente após a formatação.

### Estado final ESTRITO (validação final)

Comandos rodados no repositório `C:\Users\Leonardo\Documents\projects\fastslr`. **Nenhum arquivo do repositório foi modificado durante a validação final.**

| Verificação | Resultado |
|-------------|-----------|
| `python -m pytest -q` | **218 passed in 3.25s** — 100% verde, zero falhas |
| `python -m ruff check .` | **All checks passed!** — zero erros |
| `python -m ruff format --check .` | **42 files already formatted** — limpo |
| `python -m pyright` | **0 errors, 0 warnings, 0 informations** |

**Status final: `passed = true`** — todos os quatro gates satisfeitos.

### Check de determinismo (Fase 4–5) — ✅ OK

Triagem rodada 2x na mesma entrada (`data/Final_Corpus.csv`, `default_config.json`, `data/terms_final.csv`) via `python -m fastslr run ... -o $TEMP/fastslr_fd1 --quiet` e `_fd2`. Ambas geraram 6 artefatos cada: `triage_results.xlsx`, `protocol.json`, `config_audit.json`, `academic_report.md`, `triage_report.txt`, `academic_package.zip`.

- **`triage_results.xlsx`** (sheet `resultados`, 506 linhas × 34 colunas): a **única** coluna que difere é `run_timestamp` (timestamp por-linha). Removida essa coluna volátil, as 506 linhas são **byte-idênticas** entre as duas execuções (0 diffs nas 33 colunas de dados de triagem: ID, Title/Abstract/Tags_Highlighted, RawScore/FinalScore/BestLevel/Status/Highlights/AntiHighlights/Flags para T1A/T1B/T1C, Final_Decision, Decision_Reason, triage_version, Status_T0/Reason_T0/Scope_T0/AntiHighlights_T0/Flags_T0). **Dados de triagem idênticos.**
- **Diffs residuais** nos demais artefatos são **exclusivamente campos voláteis** (nenhum dado de triagem): `protocol.json` (`generated_at`, `execution_id`, `artifacts.results_path`, `processing.processing_time_seconds`, `processing.articles_per_second`), `config_audit.json` (`_metadata.export_timestamp`), `academic_report.md` (`Generated at`, `Execution ID`, `Processing time` 8.34s vs 8.32s, `Rate` 60.5 vs 60.7 art/s), `triage_report.txt` (`DATE`, `PROCESSING TIME`, `RATE`). Estrutura de arquivos e contagem de linhas idênticas (32/32 md, 44/44 txt).

**Conclusão: determinismo dos resultados reconfirmado.** Ambos os diretórios temporários removidos ao fim; nenhum arquivo do repositório alterado.

## Findings conscientemente NÃO aplicados

Os itens abaixo foram avaliados e **deliberadamente não corrigidos**, por não representarem risco real ao comportamento de produção:

- **Dead code em `adapters.py` / `export_raw_subset`**: código morto não-alcançável pelos fluxos atuais (CLI, TUI, controller). Não impacta resultados nem gates; remoção fica como limpeza futura de baixa prioridade, sem urgência funcional. Mantido para evitar churn fora de escopo na barreira de validação.
- **`default_config.json` — papel/`role`**: divergência cosmética/semântica de papel no config default que não altera a triagem nem quebra nenhum gate (o finding funcional correlato, `default-config-csv-false-vs-codigo-true`, **foi** resolvido no grupo io-coverage). O ajuste de `role` remanescente é puramente documental e foi conscientemente adiado.

Para o plano detalhado e a priorização original (Média/Baixa) destes itens, ver [[Validação - Auditoria Completa]] — seção **Plano de Correção**.

---

Relacionado: [[Validação - Auditoria Completa]] · [[Validação - Checklist]] · [[Home]]
