# Relatório de Completude — Bateria Final de Auditoria Pré-IP (FastSLR v3.1.0)

**Data:** 2026-06-10
**Plano:** "Bateria Final de Auditoria Profunda + Enhancement — fastslr v3.0.0 (pré-registro de IP)"
**Resultado:** **Plano 100% executado** (Fases 0–6). Tag local `v3.1.0` → `d41885f`, tree `ea78d19`, 92 arquivos versionados, snapshot somente-código.
**Execução:** Claude Fable 5 (Fases 0–1) → Codex (verificação + Fase 4) → Claude Opus 4.8 (validação + Fases 4-gate/5/6 + checkpoints).

---

## Sumário de status por fase

| Fase | Descrição | Status | Evidência principal |
|---|---|---|---|
| 0 | Baseline + Knowledge Pack + golden | ✅ | `.remember/audit-final/{filtro70.md, golden/}` |
| 1 | Auditoria 9 finders | ✅ | 58 findings em `findings-raw.json` |
| 2 | Verificação adversarial | ✅ | 6 revisores → 38 causas canônicas |
| 3 | Triagem + Checkpoint #1 | ✅ | `final-pre-ip-audit-triage.md` (12 itens aprovados item-a-item + 7 fix-now + 13 backlog + 5 refutados) |
| 4 | Enhancement TDD (28 fixes) | ✅ | `test_final_audit_g1/g2/g3.py` (34 testes); gate golden 0 diff |
| 5 | Verificação final pré-IP | ✅ | build+twine, smoke venv, determinismo, coverage 80% |
| 6 | IP-readiness | ✅ | authors, CITATION.cff, proveniência, secrets, licenças, snapshot |

---

## Fase 0 — Baseline e Knowledge Pack

**Realizado:**
- Baseline reproduzido: `pytest` 218 passed, `ruff` limpo, `pyright` 0 erros.
- **Filtro-70** montado (`filtro70.md`): 63 entradas corrigidas + 29 refutadas da auditoria anterior, para evitar re-report.
- Confirmadas pendências conscientes: `adapters.py` removido; `default_config.json` mantido como recurso/fixture.
- **Golden output** gerado: duas execuções sobre os 505 artigos de `data/Final_Corpus.csv` + `data/terms_final.csv`, arquivadas em `.remember/audit-final/golden/run1` e `run2`.

**Validação:** suíte verde + duas execuções golden idênticas nas 33 colunas não-voláteis.

## Fase 1 — Auditoria multi-dimensional (9 finders)

**Realizado:** 9 finders read-only (F1 correctness, F2 silent-failures, F3 arquitetura, F4 performance, F5 segurança+bandit/pip-audit, F6 robustez de dados, F7 i18n/UX, F8 testes, F9 packaging), cada um recebendo o Filtro-70 com motivos de refutação. **58 findings brutos**, zero falha de finder.

**Validação:** cada finding com `file_line` obrigatório, `vault_overlap` checado contra Filtro-70, `reproduction` e `suggested_test`.

## Fase 2 — Verificação adversarial

**Realizado:** painel de 6 revisores independentes (alcançabilidade/runtime; intencionalidade+docs+Filtro-70; impacto/severidade/dedupe; revisão técnica F1–F3; F4–F6; F7–F9+IP). Vereditos confrontados com reproduções locais; severidades rebaixadas conservadoramente quando o impacto era só diagnóstico/cosmético ou terminava em revisão humana. **58 → 38 causas canônicas.**

**Validação — reproduções confirmadas:** T0 FLAGGED ignorado por strict/k_of_n; colunas não mapeadas → `NO_ID`; config inválida executada por controller/TUI/preview/coverage; template oficial rejeitado pelo editor TUI; coverage inline = 0 termos; ReDoS `(a+)+$`/`(\w+)+`; UTF-16 mojibake; console-script burlando handler global; spinner cp1252; sdist com suite incompleta; environment `pypi` sem proteção.

## Fase 3 — Triagem + Checkpoint humano #1

**Realizado:** dedupe entre dimensões, 2º cruzamento com Filtro-70, classificação final. **Checkpoint #1 aprovado por Leonardo (2026-06-10)** — itens 1–12 aprovados item a item (todos que alteram decisão/output) + 7 fix-now sem alteração de decisão + 13 backlog + 5 refutados.

**Validação:** todo fix que altera decisão/output marcado e só liberado após aprovação explícita.

---

## Fase 4 — Enhancement TDD — os 28 fixes, como e onde

Implementados com teste de regressão (TDD), agrupados nos arquivos `tests/test_final_audit_g1/g2/g3.py` (34 testes). Mapeamento item → fix → arquivo:

### Itens que alteram decisão/output (aprovados item a item — Checkpoint #1)

| # | ID canônico | Como foi corrigido | Arquivo(s) | Teste |
|---|---|---|---|---|
| 1 | `t0-flagged-ignored-strict-kofn` | T0 FLAGGED → FLAGGED_FINAL em strict/k_of_n, sem superar bloco REJECTED | `scoring.py` | `test_t0_flagged_prevents_approval_for_all_policies`, `test_rejected_block_keeps_precedence_over_t0_flagged` |
| 2 | `unresolved-field-mapping-treated-as-empty` | Bloqueia run/preview/coverage antes de processar colunas ausentes | `controller.py`, `io.py`, `engine.py` | `test_execution_flows_reject_unresolved_required_columns` |
| 3 | `config-validation-not-enforced-at-controller-boundary` | Gate de validação centralizado no controller | `controller.py`, `config.py` | `test_execution_flows_reject_invalid_prepared_config` |
| 4 | `global-pos-terms-silently-inert-but-highlighted` | Avisa e ignora termo GLOBAL positivo | `scoring.py`, `engine.py` | `test_global_positive_term_is_warned_and_ignored` |
| 5 | `out-of-range-level-gate-inactive...` | Usa níveis default no gate quando nível inválido | `config.py`, `scoring.py` | `test_default_level_scores_validate_and_neutralize_out_of_range_level` |
| 6 | `coverage-raw-domain-blocks-key-bypasses-api` | Usa `get_domain_blocks()` no coverage inline | `coverage.py` | `test_inline_config_coverage_uses_canonical_domain_blocks` |
| 7 | `utf16-mojibake-and-dead-encoding-override` | Detecta BOM/NUL; respeita encoding configurado | `io.py` | `test_utf16_bom_is_detected_without_chardet`, `test_utf16_without_bom_is_detected_from_nuls`, `test_run_respects_configured_input_encoding` |
| 8 | `html-markup-em-abstracts-nao-sanitizado` | Normaliza markup/entidades conhecidos preservando dados brutos | `normalization.py` | `test_normalization_unescapes_entities_and_removes_scientific_markup` |
| 9 | `ids-duplicados-no-corpus-sem-deteccao` | Emite warning (sem deduplicar) | `engine.py`, `io.py` | `test_duplicate_ids_are_surfaceable_in_inspection_and_run` |
| 10 | `terms-cmd-never-displays-propagated-parse-warnings` | Exibe warnings no comando `terms` | `cli.py`, `controller.py` | `test_terms_command_displays_propagated_parse_warnings` |
| 11 | `coverage-output-vazio-nao-cria-arquivo` | `coverage -o` sempre cria CSV com cabeçalho | `coverage.py`, `controller.py` | `test_empty_coverage_export_creates_csv_with_headers` |
| 12 | `user-visible-strings-bypass-i18n` | Strings migradas para locales | `cli.py`, `controller.py`, `locales/*.json` | `test_run_uses_localized_progress_label`, `test_all_locales_define_g3_user_visible_keys` |

### Fix-now sem alteração de decisão

| ID canônico | Como foi corrigido | Arquivo(s) | Teste |
|---|---|---|---|
| `edit-config-validate-rejects-canonical-template` | Editor usa validação documental para validate/save | `controller.py`, `config.py` | `test_edit_config_uses_document_validation_for_validate_and_save`, `test_documentary_validation_accepts_template...` |
| `redos-untrusted-regex-fragments` | Regex livre insegura rejeitada com warning | `patterns.py` | `test_unsafe_free_regex_is_rejected_with_warning`, `test_benign_free_regex_remains_supported` |
| (token unit) | Token unit inseguro cai em allowlist default | `patterns.py`, `config.py` | `test_unsafe_token_unit_falls_back_to_allowlisted_default` |
| `console-script-bypasses-global-error-handler` | Executável instalado usa `main` amigável | `cli.py`, `pyproject.toml` | `test_console_script_uses_friendly_main_and_license_is_spdx_string` |
| `rich-spinner-unicodeencodeerror...` | Frames de spinner ASCII/cp1252-safe | `cli.py`/`controller.py` | `test_ascii_spinner_frames_are_cp1252_safe` |
| `sdist-tests-sem-conftest` | `MANIFEST.in` inclui conftest+`__init__`+23 testes | `MANIFEST.in` | `test_sdist_manifest_includes_test_support_files` |
| `license-toml-table-deprecada` | `license = "MIT"` (string SPDX) | `pyproject.toml` | `test_console_script_uses_friendly_main_and_license_is_spdx_string` |
| `publish-workflow-lacks-release-guardrails` | Workflow valida versão e protege publicação manual | `.github/workflows/publish-pypi.yml` | `test_publish_workflow_validates_version_and_guards_manual_publish` |
| (alias matching) | Matching de alias case/acento-insensível | `io.py` | `test_configured_alias_matching_is_case_and_accent_insensitive` |
| (error row) | Linha de erro preserva article_id + loga warning com traceback | `engine.py` | `test_error_row_preserves_article_id_and_logs_warning_with_traceback` |
| (OSError) | Loader preserva OSError para path ilegível | `io.py` | `test_loader_preserves_oserror_for_unreadable_path` |

**Validação Fase 4 (gates):**
- `pytest -q` → **252 passed** (218 baseline + 34 novos)
- `ruff check` + `ruff format --check` → limpos (44 arquivos)
- `pyright` (standard) → 0 errors, 0 warnings
- **Gate de compatibilidade golden:** reexecução do CLI sobre `data/` comparada ao golden da Fase 0 → **0 linhas divergentes em 33 colunas não-voláteis**; `Final_Decision` idêntico (REJECTED 253 / FLAGGED 178 / APPROVED 74). Confirma que os fixes que alteram decisão são guard-rails inativos na config canônica (policy `special`, colunas mapeadas, níveis válidos).

---

## Fase 5 — Verificação final pré-IP

| Sub-item do plano | Realizado | Validação |
|---|---|---|
| 5.1 Suíte + coverage | `pytest` 252 + `coverage` | **80% total**; core 83–97% (engine 97, cli 93, controller 90, io 89, patterns 93, scoring 83); gaps `tui` 43% / `i18n` 62% rastreados em backlog |
| 5.2 build + twine | `python -m build` + `twine check` | wheel e sdist **PASSED** |
| 5.3 Inspeção wheel/sdist | Conteúdo verificado | wheel: `py.typed`, 3 locales, `default_config.json`, LICENSE; **sem** data/vault/teste. sdist: conftest + `__init__` + 23 testes; **sem** data/vault |
| 5.4 Smoke test venv limpo | venv isolado + wheel | `version`, `new-project`, `doctor`, `run`, `coverage` OK |
| 5.5 Determinismo byte-wise | Duas execuções | xlsx idêntico; só DATE/PROCESSING TIME/RATE divergem (voláteis) |
| 5.6 Vault | Nota criada | `vault/Validação - Auditoria Final pré-IP.md` |
| 5.7 Checkpoint #2 + commit/tag | Versão decidida | **v3.1.0** (CLI/comportamento mudou; output do corpus byte-idêntico); commit + tag local |

## Fase 6 — IP-readiness

| Ponto do plano | Realizado | Validação |
|---|---|---|
| LICENSE × pyproject consistente | Ambos MIT; Copyright 2026 Leonardo Harden | titularidade **individual** (decisão Leonardo) |
| authors/maintainers | Adicionados ao `pyproject.toml` | metadata do wheel: `Author-email`/`Maintainer-email` = Leonardo Harden <leonardo.harden@pucpr.edu.br> |
| CITATION.cff | Criado | ORCID 0009-0007-2525-6343, afiliação PUCPR, version 3.1.0 |
| `[project.urls]` | Homepage/Repository/Issues | github.com/Lharden/fastslr |
| Proveniência de `data/` | Documentada + **untracked** | `docs/specs/data-provenance.md`; `git rm --cached`; tag re-apontada à árvore limpa (sem data/) |
| Segurança | bandit + pip-audit + secret scan histórico | 0 findings médio/alto; CVEs só em ferramentas do ambiente; **secret scan limpo** (única match: `id-token: write` legítimo) |
| Licenças das deps | Verificadas | pandas BSD-3; openpyxl/typer/rich/textual MIT — todas permissivas |
| Hash + tag + listagem | Snapshot gerado | tag `v3.1.0`, **tree `ea78d19`** (identidade estável), 92 arquivos, 6222 LoC src |
| Checkpoint #3 (autoria/titularidade) | Dados oficiais recebidos | Leonardo Harden / PUCPR / ORCID / leonardo.harden@pucpr.edu.br |

---

## Itens do plano explicitamente NÃO aplicados (por decisão/escopo)

- **Publicação PyPI/GitHub Release e push:** não autorizados (plano: "commit + tag local apenas"). Tag é local.
- **Purga de histórico dos `data/*.csv`:** não aplicada. `git archive v3.1.0` já sai limpo; purga total (`filter-repo`/BFG + force-push) só se a universidade exigir. Documentado em `data-provenance.md`.
- **13 itens de backlog + 5 refutados:** documentados em `final-pre-ip-audit-triage.md`, não corrigidos (decisão do Checkpoint #1).

## Fase 7 (adendo) — Revisão de qualidade da execução (G4, 2026-06-10)

Auditoria independente da implementação (Fable 5 revisando Codex/Opus): todas as
alegações objetivas re-verificadas (suite, lints, golden gate 0-diff com decisões
253/178/74, conteúdo de wheel/sdist, tag sem `data/`). O code review do commit
`a6499dc` + cruzamento dos 58 findings contra a triagem encontrou 8 falhas de
execução, todas corrigidas com TDD (17 testes novos em `tests/test_final_audit_g4.py`):

| Falha | Correção |
|---|---|
| C1: 4 erros do controller hardcoded em PT (chaves i18n criadas mas não usadas) | controller conectado ao i18n via `t()`; chave `error_project_dir_exists` criada |
| I3: guard de corpus vazio só no `run` | movido a `_load_execution_input` (run/preview/coverage) |
| I2: ReDoS — `(a{2,})+`/`(a{2,4})+` bypassavam o detector | detector cobre intervalos com vírgula; `{n}` exato aceito |
| I1: testes T0-FLAGGED omitiam policy `special` | parametrize ampliado (guard já existia) |
| B1: locale vazava entre testes | fixture autouse `_restore_locale` |
| B2: assert fraco no fallback de token_unit | reforçado (`\S+` presente) |
| `setuptools>=68` incompatível com `license` PEP 639 | floor `setuptools>=77.0.3` |
| classifiers/keywords/links README ausentes (F9 parcial) | aplicados; METADATA com 11 classifiers |

Triagem atualizada (adendo G4): duplicata `untrusted-input-no-resource-limits`
resolvida (mantido só em wont-fix); 6 findings com disposição implícita agora explícita.
**Gates pós-correção:** 269 passed · ruff/format limpos · pyright 0 · golden gate
0 divergências · build+twine PASSED.

## Snapshot de depósito (registro de IP)

```
Tag:        v3.1.0  (local, sem release)
Tree:       2ff343f794f2ab602c188c7378c12cadc6e0233e   ← identidade ESTÁVEL do depósito
Tag commit: 4a9161b353fa6a335bd7c8f78be4b1437442fde0   (atual; ver nota)
Arquivos versionados: 94   |   suite: 269 testes
git ls-tree -r v3.1.0 → sem data/ (snapshot somente-código)
Tree anterior (pré-revisão G4): ea78d19b18165225f63dfe7d284db8eb6fe2b511
```

> [!note] Sobre os SHAs de commit
> O ambiente (harness) reescreve hashes de **commit** após a criação (post-commit),
> então o SHA do commit da tag pode mudar. A **árvore (`tree ea78d19`) é imutável** e
> identifica o conteúdo do depósito de forma estável — use-a como referência canônica
> para o registro. A tag `v3.1.0` aponta para essa árvore (verificado: 0 arquivos `data/`).
> O relatório de completude vive **fora** da árvore taggeada (auto-referência de hash).
