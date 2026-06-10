---
tags: [fastslr, validacao, auditoria, ip, pre-registro]
---

# 🔬 Validação - Auditoria Final pré-IP (v3.1.0)

Bateria **final** de auditoria profunda antes da vinculação à propriedade intelectual. Partiu do estado pós-[[Validação - Auditoria Completa]] (46 corrigidos + 24 refutados). A nova rodada usou 9 finders paralelos + verificação adversarial (6 revisores), reduziu **58 findings brutos → 38 causas canônicas**, filtrou contra o Filtro-70 e levou **28 itens fix-now** ao Checkpoint humano #1 (aprovados item a item em 2026-06-10). Todos os 28 foram implementados com TDD (34 testes novos), e a release foi promovida a **v3.1.0** (titularidade individual, Leonardo Harden). **Nenhuma decisão de triagem mudou sobre o corpus oficial** — os fixes que alteram decisão são guard-rails que só disparam em configs/dados de borda fora da config canônica.

## Resumo

| Métrica | Valor |
|---------|-------|
| Findings brutos (Fase 1) | 58 |
| Causas canônicas (pós-dedupe) | 38 |
| Fix-now aprovados e implementados | 28 |
| Documentar / backlog | 13 |
| Refutados / wont-fix | 5 |
| Testes (antes → depois) | 218 → 252 |
| Diff golden no corpus oficial | **0 linhas** (33 colunas não-voláteis) |

## Fixes implementados (28) — destaques

- **t0-flagged-ignored-strict-kofn** (Alta): T0 FLAGGED agora resulta em FLAGGED_FINAL em `strict`/`k_of_n`, sem superar bloco REJECTED. Policy `special` (config oficial) já era correta → sem mudança no golden.
- **unresolved-field-mapping-treated-as-empty** (Alta): colunas obrigatórias ausentes bloqueiam run/preview/coverage antes de processar (eliminado `NO_ID` + rejeição silenciosa).
- **config-validation-not-enforced-at-controller-boundary** (Alta): gate de validação centralizado no controller — TUI/API/preview/coverage não executam mais config inválida.
- **utf16-mojibake-and-dead-encoding-override** (Média): detecção de BOM/NUL antes do decode; encoding configurado respeitado.
- **redos-untrusted-regex-fragments** (Média): regex livre de terceiros com backtracking exponencial rejeitada com warning; token unit inseguro cai em allowlist.
- **coverage-raw-domain-blocks-key-bypasses-api** (Média): coverage inline usa `get_domain_blocks()` (não retorna mais zero termos).
- **console-script-bypasses-global-error-handler** (Média): executável instalado usa o `main` amigável.
- **rich-spinner-unicodeencodeerror...** (Média): frames de spinner ASCII/cp1252-safe sob redirect.
- **sdist-tests-sem-conftest** (Média): `MANIFEST.in` inclui `conftest.py`, `__init__.py` e os 23 `test_*.py`.
- **publish-workflow-lacks-release-guardrails** (Média): workflow valida versão e protege publicação manual.
- **license-toml-table-deprecada** (Baixa): `license = "MIT"` (string SPDX).
- Demais: global positivo avisado/ignorado, nível fora do range neutralizado, IDs duplicados sinalizáveis, warnings de `terms` exibidos, `coverage -o` sempre cria CSV, strings migradas para i18n, editor TUI aceita o template canônico.

## Evidência de verificação (sessão 2026-06-10)

| Gate | Resultado |
|------|-----------|
| `pytest -q` | **252 passed** |
| `ruff check` / `format --check` | limpo / 44 arquivos formatados |
| `pyright` (standard) | 0 errors, 0 warnings |
| Gate golden (corpus oficial, 505 artigos) | **0 diferenças** em 33 colunas não-voláteis; Final_Decision REJECTED 253 / FLAGGED 178 / APPROVED 74 idêntico |
| `python -m build` + `twine check` | wheel e sdist **PASSED** |
| Conteúdo wheel | `py.typed`, 3 locales, `default_config.json`, LICENSE; **sem** data/vault/teste |
| Conteúdo sdist | inclui conftest + 23 testes; **sem** data/vault |
| Smoke (venv limpo) | version, new-project, doctor, run, coverage OK |
| Determinismo | xlsx idêntico; só DATE/PROCESSING TIME/RATE divergem (voláteis) |
| Secret scan (histórico) | limpo (única correspondência: `id-token: write` legítimo) |
| Licenças deps | pandas BSD-3; openpyxl/typer/rich/textual MIT — todas permissivas |
| Bandit / pip-audit | 0 findings médio/alto; CVEs só em ferramentas do ambiente |

## IP-readiness

- LICENSE MIT — **Copyright 2026 Leonardo Harden** (titularidade individual, decisão de 2026-06-10).
- `pyproject.toml`: adicionados `authors`/`maintainers` (Leonardo Harden, leonardo.harden@pucpr.edu.br) e `[project.urls]`.
- `CITATION.cff` criado (ORCID 0009-0007-2525-6343, afiliação PUCPR).
- Proveniência dos dados documentada em [[../docs/specs/data-provenance|data-provenance]].

> [!warning] Risco de IP em aberto
> `data/Final_Corpus.csv` e `data/terms_final.csv` **estão versionados no git e no histórico** (apesar de `.gitignore` listar `data/` e a distribuição os excluir). Contêm metadados/abstracts bibliográficos de terceiros. Para um snapshot de depósito **somente-código**, avaliar `git rm --cached` (going-forward) ou purga de histórico — decisão do Leonardo/universidade. Não alterado nesta sessão.

## Backlog / Refutados

Registrados em [[../docs/specs/final-pre-ip-audit-triage|final-pre-ip-audit-triage]]: 13 itens documentar/backlog (ex.: prefilter literal no matching, broad-except com logging na app layer, cobertura de regressão em paths de decisão) e 5 refutados (ex.: `parse-terms-except-amplo` inalcançável; duplicação MENU_ITEMS sincronizada).
