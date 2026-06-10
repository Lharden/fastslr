# Triagem Consolidada - Auditoria Final Pre-IP

**Data:** 2026-06-10  
**Entrada:** 58 findings brutos em `.remember/audit-final/findings-raw.json`  
**Filtro:** 63 entradas corrigidas e 29 refutadas registradas no Filtro-70  
**Resultado:** 38 causas canônicas apos deduplicacao

## Checkpoint Humano #1

O plano original exige aprovacao da lista `fix-now` e aprovacao item a item para
qualquer mudanca que altere decisoes de triagem ou formato de output.

**Decisao de 2026-06-10:** Leonardo aprovou os itens 1-12, incluindo as propostas
explicadas para GLOBAL positivo, niveis fora do range, warnings do comando `terms`,
arquivo vazio de `coverage -o` e localizacao de strings.

### Aprovados Item A Item

| ID canonico | Severidade | Efeito confirmado | Mudanca proposta |
|---|---|---|---|
| `t0-flagged-ignored-strict-kofn` | Alta | T0 FLAGGED vira APPROVED em `strict`/`k_of_n` | Fazer T0 FLAGGED resultar em FLAGGED_FINAL sem superar bloco REJECTED |
| `unresolved-field-mapping-treated-as-empty` | Alta | Colunas ausentes geram `NO_ID` e rejeicoes silenciosas | Bloquear run/preview/coverage antes de processar |
| `config-validation-not-enforced-at-controller-boundary` | Alta | TUI/API/preview/coverage executam config invalida | Centralizar gate no controller |
| `global-pos-terms-silently-inert-but-highlighted` | Baixa/Media | Termo GLOBAL positivo e destacado mas nao decide | Avisar e ignorar termo GLOBAL positivo |
| `out-of-range-level-gate-inactive-without-pontuacao-niveis` | Baixa/Media | Nivel invalido pode mudar APPROVED para FLAGGED | Usar niveis default no gate |
| `coverage-raw-domain-blocks-key-bypasses-api` | Media | Coverage inline retorna zero termos | Usar `get_domain_blocks()` |
| `utf16-mojibake-and-dead-encoding-override` | Media | UTF-16 vira lixo silencioso e altera decisoes | Detectar BOM/NUL e encanar encoding |
| `html-markup-em-abstracts-nao-sanitizado` | Baixa | Markup causa falsos negativos | Normalizar markup conhecido preservando dados brutos |
| `ids-duplicados-no-corpus-sem-deteccao` | Baixa | Contagens e protocolo podem inflar | Emitir warning, sem deduplicar |
| `terms-cmd-never-displays-propagated-parse-warnings` | Baixa | Termos descartados ficam invisiveis | Exibir warnings no comando `terms` |
| `coverage-output-vazio-nao-cria-arquivo` | Baixa | `coverage -o` pode nao criar artefato | Sempre criar CSV com cabecalho ou avisar |
| `user-visible-strings-bypass-i18n` | Baixa | Mensagens/label misturam idiomas | Migrar strings para locales |

### Fix-Now Sem Alteracao de Decisao de Triagem

| ID canonico | Severidade | Justificativa |
|---|---|---|
| `edit-config-validate-rejects-canonical-template` | Media | Editor TUI recusa o template criado pelo proprio produto |
| `redos-untrusted-regex-fragments` | Media | Dois vetores reproduzidos de backtracking exponencial |
| `console-script-bypasses-global-error-handler` | Media | Executavel instalado mostra traceback; `python -m` nao |
| `rich-spinner-unicodeencodeerror-masks-error-message-on-redirect` | Media | Spinner cp1252 mascara erro amigavel |
| `sdist-tests-sem-conftest-suite-quebrada` | Media | Sdist: 200 passed, 2 skipped, 16 errors |
| `license-toml-table-deprecada` | Baixa | Build avisa enforcement em 2027-02-18 |
| `publish-workflow-lacks-release-guardrails` | Media | Environment sem protecao; refs moveis; sem tag-versao |

### Documentar / Backlog

- `level-order-param-parsed-documented-never-used`
- `configured-level-missing-thresholds-silent-flag-only`
- `delimited-input-errors-collapsed-to-encoding-message`
- `engine-err-row-descarta-article-id-e-loga-so-em-debug`
- `profileinfo-dataclass-defined-twice`
- `app-layer-broad-except-without-logging`
- `regex-matching-lacks-literal-prefilter`
- `normalizacao-resub-sequencial-padroes-reconstruidos`
- `decision-critical-paths-lack-regression-coverage`
- `terms-parse-warning-paths-sem-cobertura`
- `diff-fallback-id-primeira-coluna-sem-teste`
- `package-metadata-and-pypi-onboarding-incomplete`
- `cli-run-double-prepare-config-private-api` (config preparada/validada 2x no
  caminho `run` da CLI; redundância de desempenho, sem efeito funcional)

### Refutados / Wont-Fix

- `parse-terms-except-amplo-descarta-linha-sem-warning`: inalcançavel no fluxo suportado.
- `dashboard-menu-four-way-duplication-unguarded`: risco futuro, estruturas sincronizadas.
- `tui-worker-residual-query-one-from-thread`: mutacoes ja usam `call_from_thread`;
  `query_one` no worker e aceito em exemplo oficial do Textual.
- `load-delimited-parse-triplo-todos-separadores`: trade-off de robustez; otimizar apenas
  com benchmark e equivalencia.
- `untrusted-input-no-resource-limits`: hardening amplo sem contrato ou repro especifica.

## Adendo — Revisão de execução (G4, 2026-06-10)

Auditoria de qualidade da execução (Fable 5 revisando a implementação
Codex/Opus) encontrou e corrigiu, com regressão em `tests/test_final_audit_g4.py`:

| ID | Problema na execução | Correção |
|---|---|---|
| `controller-errors-hardcoded-pt` (C1) | Fix i18n criou as chaves mas o controller seguiu com 4 mensagens hardcoded em PT | controller usa `t()` em empty-corpus/diff/export/new-project; nova chave `error_project_dir_exists` nas 3 locales |
| `empty-corpus-guard-run-only` (I3) | Guard de corpus vazio só em `run_triage` | movido para `_load_execution_input` (cobre run/preview/coverage) |
| `redos-interval-quantifier-bypass` (I2) | `(a{2,})+`/`(a{2,4})+` passavam pelo detector | detector amplia quantificador interno para intervalos com vírgula; `{n}` exato segue aceito |
| `t0-flagged-special-sem-cobertura` (I1) | Testes "all policies" omitiam `special` | parametrize ampliado (guard já existia) |
| `locale-leak-entre-testes` (B1) | `set_locale` vazava entre testes | fixture autouse `_restore_locale` no conftest |
| `token-unit-fallback-assert-fraco` (B2) | Assert não verificava o fallback `\S+` | assert reforçado |
| `setuptools-floor-pep639` | `license = "MIT"` (PEP 639) com `setuptools>=68` quebraria rebuild | floor elevado a `setuptools>=77.0.3` |
| `classifiers-keywords-readme-links` | Itens de F9 sem aplicação | classifiers+keywords no pyproject; links absolutos no README |

Disposições esclarecidas (estavam implícitas): `alias-configurado-case-sensitive-assimetrico`
e `progress-label-triage-hardcoded-english` foram CORRIGIDOS na Fase 4 (testes
`test_configured_alias_matching_is_case_and_accent_insensitive` e
`test_run_uses_localized_progress_label`); `project-authors-maintainers-ausentes` e a
parte de URLs de `project-urls-classifiers-keywords-ausentes` foram corrigidos na Fase 6;
`readme-links-relativos-quebrados-na-pagina-pypi` e classifiers/keywords corrigidos neste adendo.
Nota de contagem: `untrusted-input-no-resource-limits` constava em backlog E em
wont-fix; mantido apenas em wont-fix.

## Evidencias Chave

- Baseline: `218 passed`, Ruff limpo, Pyright 0 erros.
- T0 FLAGGED: `special -> FLAGGED_FINAL`; `strict/k_of_n -> APPROVED_FINAL`.
- Mapping ausente: run conclui com `ID=NO_ID` e `REJECTED_FINAL`.
- Console script: `fastslr` mostra traceback; `python -m fastslr` mostra erro amigavel.
- ReDoS: `(a+)+$` e `(\w+)+` demonstraram crescimento exponencial.
- Sdist: `200 passed, 2 skipped, 16 errors` por ausencia de `conftest.py`.
- Determinismo: duas execucoes golden iguais em todas as 33 colunas nao-volateis.
- Bandit: zero findings de severidade media/alta.
- `pip-audit`: CVEs apenas em ferramentas do ambiente, nao nas dependencias runtime.
