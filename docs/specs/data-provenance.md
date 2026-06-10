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

## Risco em aberto (decisão Leonardo/universidade)

`Final_Corpus.csv` e `terms_final.csv` estão **versionados no git e presentes no histórico**.
O corpus contém abstracts/metadados bibliográficos de terceiros (titularidade dos
editores/autores originais). Para um snapshot de depósito **somente-código**:

1. **Going-forward:** `git rm --cached data/Final_Corpus.csv data/terms_final.csv`
   (mantém os arquivos em disco, remove do índice; `.gitignore` já cobre `data/`).
2. **Histórico:** purga via `git filter-repo`/BFG se o depósito exigir ausência total.
3. **Manter:** se a universidade considerar uso acadêmico de fair use/citação suficiente.

Nenhuma ação foi aplicada nesta sessão; aguarda decisão formal.

## Licenças de dependências (runtime)

Todas permissivas, compatíveis com depósito MIT:

| Pacote | Licença |
|---|---|
| pandas | BSD 3-Clause |
| openpyxl | MIT |
| typer | MIT |
| rich | MIT |
| textual | MIT |
