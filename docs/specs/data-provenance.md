# Proveniência dos Dados — Dossiê de IP

**Data:** 2026-06-10
**Contexto:** Registro de propriedade intelectual do software FastSLR (código), não do corpus.

## Escopo do depósito

O ativo de IP é o **software FastSLR** (CLI/TUI determinístico para triagem de SLR).
Os arquivos de dados sob `data/` são **insumos de teste/validação** da pesquisa do autor,
não fazem parte do produto distribuível e **são excluídos do wheel e do sdist**
(verificado na Fase 5: `tool.setuptools.package-data` lista apenas `py.typed`,
`i18n/locales/*.json`, `core/*.json`).

## Inventário de `data/`

| Arquivo | Tracked no git | Distribuído (wheel/sdist) | Natureza |
|---|---|---|---|
| `data/Final_Corpus.csv` | **Sim** | Não | Metadados bibliográficos + abstracts de terceiros (corpus da SLR) |
| `data/Final_Corpus_Raw.csv` | Não | Não | Versão bruta do corpus |
| `data/terms_final.csv` | **Sim** | Não | Termos de busca ponderados (autoria do pesquisador) |

## Decisão aplicada (2026-06-10)

Leonardo decidiu manter esses insumos (corpus da RSL + termos, com abstracts de
terceiros) **fora do git**, preservados em disco.

- **Executado:** `git rm --cached data/Final_Corpus.csv data/terms_final.csv` (commit de
  untrack). Arquivos mantidos em disco; `.gitignore` já cobre `data/`. A tag **v3.1.0 foi
  re-apontada** para a árvore limpa — o snapshot de depósito é **somente-código** (sem
  `data/` em `git ls-tree -r v3.1.0`).
- **Resíduo de histórico:** commits anteriores ainda contêm os CSVs. Um *archive* da tag
  (`git archive v3.1.0`) já sai limpo. Purga total do histórico (`git filter-repo`/BFG +
  force-push) só é necessária se o depósito exigir ausência absoluta no histórico — não
  aplicada (remoto público já contém o histórico; decisão da universidade).

## Licenças de dependências (runtime)

Todas permissivas, compatíveis com depósito MIT:

| Pacote | Licença |
|---|---|
| pandas | BSD 3-Clause |
| openpyxl | MIT |
| typer | MIT |
| rich | MIT |
| textual | MIT |
