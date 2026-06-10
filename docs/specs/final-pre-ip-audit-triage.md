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
- `untrusted-input-no-resource-limits`
- `decision-critical-paths-lack-regression-coverage`
- `terms-parse-warning-paths-sem-cobertura`
- `diff-fallback-id-primeira-coluna-sem-teste`
- `package-metadata-and-pypi-onboarding-incomplete`

### Refutados / Wont-Fix

- `parse-terms-except-amplo-descarta-linha-sem-warning`: inalcançavel no fluxo suportado.
- `dashboard-menu-four-way-duplication-unguarded`: risco futuro, estruturas sincronizadas.
- `tui-worker-residual-query-one-from-thread`: mutacoes ja usam `call_from_thread`;
  `query_one` no worker e aceito em exemplo oficial do Textual.
- `load-delimited-parse-triplo-todos-separadores`: trade-off de robustez; otimizar apenas
  com benchmark e equivalencia.
- `untrusted-input-no-resource-limits`: hardening amplo sem contrato ou repro especifica.

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
