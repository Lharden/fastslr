# FastSLR v3.0.0

[![PyPI](https://img.shields.io/pypi/v/fastslr.svg)](https://pypi.org/project/fastslr/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/fastslr.svg)](https://pypi.org/project/fastslr/)

**Triagem determinística universal para Revisões Sistemáticas de Literatura**

FastSLR processa artigos acadêmicos através de um pipeline de filtragem multi-estágio, permitindo seleção rápida, reproduzível e auditável para sua RSL. Sem machine learning — resultados 100% determinísticos.

> 📖 **Novo por aqui?** Comece pelo [**Guia do Usuário completo**](docs/GUIA_DO_USUARIO.md) — manual passo-a-passo com instalação, configuração, todas as opções, exemplos por área e troubleshooting.

---

## Índice

- [Instalação](#instalação)
- [Início Rápido](#início-rápido)
- [Conceitos Fundamentais](#conceitos-fundamentais)
- [Configuração](#configuração)
- [Criando o Arquivo de Termos](#criando-o-arquivo-de-termos)
- [Comandos CLI](#comandos-cli)
- [Interface TUI](#interface-tui)
- [Fluxo de Trabalho Recomendado](#fluxo-de-trabalho-recomendado)
- [Interpretando Resultados](#interpretando-resultados)
- [Exportação Acadêmica](#exportação-acadêmica)
- [Perfis de Configuração](#perfis-de-configuração)
- [Internacionalização](#internacionalização)
- [Uso Programático](#uso-programático)
- [FAQ](#faq)

---

## Instalação

### Requisitos

- Python >= 3.10

### Via pip (recomendado)

```bash
pip install fastslr
```

Confirme a instalação:

```bash
fastslr version
```

### Versão de desenvolvimento (GitHub)

Para a versão mais recente do repositório, ou uma tag específica:

```bash
pip install git+https://github.com/Lharden/fastslr.git
pip install git+https://github.com/Lharden/fastslr.git@v3.0.0
```

### Desenvolvimento local

```bash
git clone https://github.com/Lharden/fastslr.git
cd fastslr
pip install -e ".[dev]"
```

### Dependência opcional (detecção de encoding)

Opcional — o FastSLR já tenta automaticamente uma cadeia de codificações (utf-8 / cp1252 / latin-1). Para ativar a detecção via `chardet`:

```bash
pip install "fastslr[chardet]"
```

---

## Início Rápido

### 1. Crie um novo projeto

```bash
fastslr new-project meu-projeto --blocks "CTX,TECH,SCM" --preset standard
```

Isso cria uma pasta `meu-projeto/` com:
- `config.json` — configuração pronta para uso
- `terms.xlsx` — template principal de termos para você preencher
- `terms.csv` — cópia alternativa para scripts/versionamento

### 2. Edite o arquivo de termos

Abra `terms.xlsx` e adicione seus termos de busca (veja a seção [Criando o Arquivo de Termos](#criando-o-arquivo-de-termos)).

### 3. Verifique o setup

```bash
fastslr doctor --input artigos.csv --config meu-projeto/config.json --terms meu-projeto/terms.xlsx
```

O comando mostra se os arquivos existem, quais colunas foram detectadas e qual comando de run usar.

### 4. Execute a triagem

```bash
fastslr run artigos.csv --config meu-projeto/config.json --terms meu-projeto/terms.xlsx
```

### 5. Confira os resultados

Os resultados estão na pasta `output/`:
- `triage_results.xlsx` — resultados completos com scores e decisões
- `triage_report.txt` — relatório com estatísticas
- `academic_package.zip` — pacote pronto para publicação

---

## Conceitos Fundamentais

### O que são Blocos de Domínio?

Blocos são **dimensões temáticas** da sua revisão. Cada bloco avalia os artigos sob uma perspectiva diferente. Por exemplo, em uma RSL sobre "Machine Learning em Supply Chain":

| Bloco | Sigla | O que avalia |
|-------|-------|-------------|
| Contexto | CTX | O artigo é sobre supply chain? |
| Tecnologia | TECH | O artigo usa machine learning? |
| Escopo | SCM | O artigo aborda gestão de cadeia de suprimentos? |

Um artigo precisa ser aprovado nos blocos relevantes para ser incluído na RSL.

### Níveis de Importância

Cada termo positivo recebe um nível de 1 (mais importante) a 5 (menos importante):

| Nível | Significado | Pontuação Padrão |
|-------|------------|-----------------|
| 1 | Essencial / exato | 10 pontos |
| 2 | Muito relevante | 8 pontos |
| 3 | Relevante | 6 pontos |
| 4 | Parcialmente relevante | 4 pontos |
| 5 | Tangencial | 2 pontos |

### Decisões Possíveis

| Decisão | Significado | Ação Recomendada |
|---------|-----------|------------------|
| `APPROVED_FINAL` | Artigo relevante para a RSL | Incluir na revisão |
| `FLAGGED_FINAL` | Artigo possivelmente relevante | Revisão manual necessária |
| `REJECTED_FINAL` | Artigo não relevante | Excluir da revisão |

### Pré-triagem T0

O estágio T0 é um filtro global **antes** dos blocos de domínio. Serve para excluir rapidamente artigos obviamente fora do escopo (ex: "book review", "editorial").

---

## Configuração

### Estrutura do config.json

O arquivo de configuração controla todo o comportamento do sistema:

```json
{
  "global": {
    "DECISION_POLICY": "special",
    "PONTUACAO_NIVEIS": {"1": 10, "2": 8, "3": 6, "4": 4, "5": 2},
    "LIMITES_APROVADO": {"1": 10, "2": 12, "3": 18, "4": 22, "5": null},
    "LIMITES_SINALIZADO": {"1": 6, "2": 6, "3": 6, "4": 7, "5": 12},
    "WEIGHTS": {"title": 2.0, "abstract": 1.0, "manual_tags": 1.5},
    "NO_TAGS_UPLIFT": 1.17,
    "MAX_SECTION_SCORE": 30,
    "FAIL_FAST_GLOBAL": true,
    "ENABLE_PROXIMITY_DETECTION": true,
    "NOISE_PROFILE": "relaxed",
    "ERROR_POLICY": "flag"
  },
  "fields": {
    "id": "key",
    "title": "title",
    "abstract": "abstract",
    "manual_tags": "manual_tags"
  },
  "output": {
    "csv": false,
    "xlsx": true,
    "academic_package": true
  }
}
```

### Parâmetros Globais

| Parâmetro | Padrão | Descrição |
|-----------|--------|-----------|
| `DECISION_POLICY` | `"special"` | Política de decisão final: `"special"`, `"strict"` ou `"k_of_n"` |
| `PONTUACAO_NIVEIS` | `{1:10, 2:8, ...}` | Pontuação atribuída a cada nível de importância |
| `LIMITES_APROVADO` | `{1:10, 2:12, ...}` | Score mínimo para aprovação, por nível |
| `LIMITES_SINALIZADO` | `{1:6, 2:6, ...}` | Score mínimo para sinalização, por nível |
| `WEIGHTS` | `{title:2, abstract:1, tags:1.5}` | Peso de cada seção do artigo no cálculo de score |
| `NO_TAGS_UPLIFT` | `1.17` | Multiplicador aplicado quando manual_tags está vazio |
| `MAX_SECTION_SCORE` | `30` | Pontuação máxima por seção (cap) |
| `FAIL_FAST_GLOBAL` | `true` | Se um bloco rejeitar, pula os blocos seguintes |
| `ENABLE_PROXIMITY_DETECTION` | `true` | Detecta termos compostos automaticamente |
| `NOISE_PROFILE` | `"relaxed"` | Perfil de filtragem: `"relaxed"` ou `"strict"` |
| `ERROR_POLICY` | `"flag"` | Tratamento de erros: `"flag"` (sinaliza) ou `"fail"` (para) |

### Políticas de Decisão

**`"special"` (recomendada):** Se qualquer bloco rejeitar, o artigo é rejeitado. Possui regra especial: se apenas 1 bloco estiver sinalizado e os demais aprovados com score alto, o artigo pode ser aprovado.

**`"strict"`:** Todos os blocos devem aprovar para o artigo ser aprovado.

**`"k_of_n"`:** Pelo menos K blocos devem aprovar. Configure `MIN_APPROVED_BLOCKS` no config.

### Mapeamento de Campos

A seção `fields` mapeia os nomes das colunas do seu CSV de entrada:

```json
{
  "fields": {
    "id": "Key",
    "title": "Title",
    "abstract": "Abstract Note",
    "manual_tags": "Manual Tags"
  }
}
```

O sistema também faz auto-detecção de colunas comuns (Zotero, Scopus, Web of Science).

---

## Criando o Arquivo de Termos

O arquivo `terms.xlsx` define **todos os termos de busca** organizados por bloco. O mesmo formato também é aceito em CSV com separador `;`.

### Formato

```csv
block;kind;term;level;section_scope;is_regex;normalization_type;normalization_target
```

### Colunas

| Coluna | Obrigatório | Valores | Descrição |
|--------|-------------|---------|-----------|
| `block` | Sim | Nome do bloco (ex: `CTX`, `TECH`) ou `GLOBAL` | Bloco ao qual o termo pertence |
| `kind` | Sim | `pos`, `anti`, `flag` | Tipo: positivo, anti-exclusão, anti-sinalização |
| `term` | Sim | Texto livre | O termo de busca |
| `level` | Para `pos` | `1` a `5` | Nível de importância (1 = mais importante) |
| `section_scope` | Não | `any`, `title`, `abstract`, `manual_tags` | Onde buscar (padrão: `any`) |
| `is_regex` | Não | `0` ou `1` | Se o termo é uma expressão regular |
| `normalization_type` | Não | `abbreviation`, `compound_variant`, `symbol_replacement` | Tipo de regra de normalização |
| `normalization_target` | Não | Texto | Forma normalizada do termo |

### Tipos de Termos

**Positivos (`pos`):** Termos que indicam relevância. Contribuem para o score.
```csv
TECH;pos;machine learning;1;any;0;;
TECH;pos;deep learning;1;any;0;;
TECH;pos;optim*;3;any;0;;
```

**Anti-exclusão (`anti`):** Se encontrados, o artigo é **imediatamente rejeitado** no bloco.
```csv
TECH;anti;systematic review;;any;0;;
TECH;anti;meta-analysis;;any;0;;
```

**Anti-sinalização (`flag`):** Se encontrados, o artigo é **rebaixado de APPROVED para FLAGGED**.
```csv
CTX;flag;conference abstract;;any;0;;
```

**Termos globais (`GLOBAL`):** Aplicados no estágio T0, antes de qualquer bloco.
```csv
GLOBAL;anti;book review;;any;0;;
GLOBAL;flag;editorial;;any;0;;
```

### Recursos Avançados

**Wildcards:** Use `*` para corresponder a qualquer sequência de caracteres.
```csv
TECH;pos;optim*;3;any;0;;       # Corresponde a: optimize, optimization, optimal...
```

**Regex:** Ative `is_regex=1` para expressões regulares completas.
```csv
TECH;pos;ML|AI|DL;2;title;1;;   # Corresponde a: ML, AI ou DL no titulo
```

**Termos compostos:** Termos com "and", "&", "or" ou "/" são automaticamente expandidos para busca por proximidade.
```csv
CTX;pos;oil and gas;1;any;0;;   # Busca "oil...gas" ou "gas...oil" com ate 2 palavras entre eles
```

**Normalização:** Defina regras para expandir abreviaturas e unificar variantes.
```csv
TECH;pos;AI;1;any;0;abbreviation;artificial intelligence
CTX;pos;supply-chain;2;any;0;compound_variant;supply chain
```

---

## Comandos CLI

### `fastslr run` — Executar triagem

```bash
fastslr run artigos.csv -c config.json -t terms.xlsx [-o output/] [-l pt_BR] [-q]
```

| Flag | Descrição |
|------|-----------|
| `-c, --config` | Caminho para o config.json (obrigatório) |
| `-t, --terms` | Caminho para o terms.xlsx ou terms.csv |
| `-o, --output` | Diretório de saída (padrão: `output/` junto ao input) |
| `-l, --lang` | Idioma da interface: `en`, `pt_BR`, `es` |
| `-q, --quiet` | Suprime saída no terminal |

### `fastslr doctor` — Verificar setup antes da run

```bash
fastslr doctor --input artigos.csv -c config.json -t terms.xlsx
```

Mostra mapeamento de colunas detectado, blocos carregados, quantidade de termos válidos, avisos de configuração e o comando exato para executar a triagem.

### `fastslr preview` — Pré-visualizar resultados

Executa a triagem em uma **amostra** de artigos para validação rápida.

```bash
fastslr preview artigos.csv -c config.json -t terms.xlsx [-s 50]
```

| Flag | Descrição |
|------|-----------|
| `-s, --sample` | Número de artigos na amostra (padrão: 50) |

### `fastslr coverage` — Análise de cobertura

Identifica termos mortos (0 matches), termos amplos demais (>80% dos artigos) e blocos sem discriminação.

```bash
fastslr coverage artigos.csv -c config.json -t terms.xlsx [-o cobertura.csv]
```

### `fastslr diff` — Comparar duas execuções

```bash
fastslr diff resultado_v1.xlsx resultado_v2.xlsx
```

Mostra artigos cuja decisão mudou entre as duas versões, com resumo de transições.

### `fastslr new-project` — Criar novo projeto

```bash
fastslr new-project meu-projeto -b "CTX,TECH,SCM" [-p standard]
```

| Flag | Descrição |
|------|-----------|
| `-b, --blocks` | Nomes dos blocos separados por vírgula (obrigatório) |
| `-p, --preset` | Preset de níveis: `binary`, `simple`, `standard` (padrão) |
| `-o, --output` | Diretório de saída |

### `fastslr export` — Exportar pacote acadêmico

```bash
fastslr export resultado.xlsx [-o output/] [-c config.json]
```

Gera um ZIP com todos os artefatos de auditoria para publicação.

### `fastslr terms` — Navegar termos configurados

```bash
fastslr terms -c config.json -t terms.xlsx [-b TECH] [-k pos]
```

| Flag | Descrição |
|------|-----------|
| `-b, --block` | Filtrar por bloco |
| `-k, --kind` | Filtrar por tipo: `pos`, `anti`, `flag` |

### `fastslr profile` — Gerenciar perfis

```bash
# Salvar configuração como perfil
fastslr profile save meu-perfil -c config.json -d "Descricao do perfil"

# Carregar perfil para config.json
fastslr profile load meu-perfil [-o config.json]

# Listar perfis salvos
fastslr profile list
```

Perfis são salvos em `~/.fastslr/profiles/`.

### `fastslr tui` — Interface interativa

```bash
fastslr tui
```

Abre a interface gráfica no terminal (veja a próxima seção).

### `fastslr version` — Versão

```bash
fastslr version
```

---

## Interface TUI

A TUI (Terminal User Interface) oferece uma interface gráfica completa no terminal. Inicie com:

```bash
fastslr tui
```

### Telas Disponíveis

| # | Tela | Função |
|---|------|--------|
| 1 | New Project | Criar novo projeto com presets |
| 2 | Load Profile | Carregar configuração salva |
| 3 | Edit Configuration | Ajustar thresholds e parâmetros |
| 4 | Browse Terms | Visualizar e filtrar termos por bloco |
| 5 | Run Triage | Executar triagem com barra de progresso |
| 6 | Results Explorer | Navegar resultados da triagem |
| 7 | Coverage Analysis | Analisar cobertura de termos |
| 8 | Compare Runs | Comparar duas execuções |
| 9 | Export Package | Gerar pacote acadêmico |
| 10 | Settings & Language | Configurar idioma |

---

## Fluxo de Trabalho Recomendado

### Etapa 1: Preparação

1. Exporte seus artigos do gerenciador bibliográfico (Zotero, Scopus ou Web of Science) em CSV
2. Crie o projeto: `fastslr new-project minha-rsl -b "CTX,TECH,APP"`
3. Defina seus termos no `terms.xlsx`

### Etapa 2: Calibração

4. Verifique o setup: `fastslr doctor --input artigos.csv -c config.json -t terms.xlsx`
5. Execute um preview: `fastslr preview artigos.csv -c config.json -t terms.xlsx -s 100`
6. Analise a distribuição de decisões
7. Ajuste thresholds e termos conforme necessário
8. Execute análise de cobertura: `fastslr coverage artigos.csv -c config.json -t terms.xlsx`
9. Remova termos mortos, refine termos amplos demais

### Etapa 3: Execução

10. Execute a triagem completa: `fastslr run artigos.csv -c config.json -t terms.xlsx`
11. Revise manualmente os artigos `FLAGGED_FINAL`
12. Documente decisões manuais

### Etapa 4: Documentação

13. Exporte o pacote acadêmico, se precisar regenerar o ZIP: `fastslr export resultado.xlsx`
14. Inclua o `protocol.json` como material suplementar na publicação
15. Use o `config_hash` para garantir reprodutibilidade

### Etapa 5: Iteração (se necessário)

16. Ajuste termos e thresholds
17. Re-execute: `fastslr run artigos.csv -c config.json -t terms.xlsx`
18. Compare com a execução anterior: `fastslr diff resultado_v1.xlsx resultado_v2.xlsx`

---

## Interpretando Resultados

### Colunas do Excel de Saída

| Coluna | Descrição |
|--------|-----------|
| `ID` | Identificador do artigo |
| `Title_Highlighted` | Título com termos encontrados marcados como `***TERMO***` |
| `Abstract_Highlighted` | Resumo com termos marcados |
| `Tags_Highlighted` | Tags com termos marcados |
| `RawScore_<BLOCO>` | Pontuação bruta do bloco |
| `FinalScore_<BLOCO>` | Pontuação final (após uplift) |
| `BestLevel_<BLOCO>` | Melhor nível de importância encontrado |
| `Status_<BLOCO>` | Decisão do bloco: APPROVED, FLAGGED, REJECTED |
| `Highlights_<BLOCO>` | Detalhes dos matches positivos |
| `AntiHighlights_<BLOCO>` | Detalhes dos anti-termos de exclusão |
| `Flags_<BLOCO>` | Detalhes dos anti-termos de sinalização |
| `Final_Decision` | Decisão final: APPROVED_FINAL, FLAGGED_FINAL, REJECTED_FINAL |
| `Decision_Reason` | Explicação da decisão |
| `Status_T0` | Status do pré-filtro global (se configurado) |

### Como Ler os Scores

- **Score alto + APPROVED:** artigo claramente relevante
- **Score moderado + FLAGGED:** artigo na fronteira, requer revisão manual
- **Score baixo + REJECTED:** artigo fora do escopo
- **REJECTED por anti-termo:** artigo excluído por termo de exclusão, independente do score

### Dicas de Interpretação

1. **Muitos FLAGGED?** Considere relaxar os thresholds de aprovação
2. **Muitos REJECTED?** Revise se seus termos cobrem sinônimos e variantes
3. **Poucos REJECTED?** Seus termos podem ser amplos demais; use `coverage` para verificar
4. **Scores inesperados?** Verifique o `Highlights` para entender quais termos foram encontrados

---

## Exportação Acadêmica

O pacote acadêmico (`academic_package.zip`) contém tudo necessário para reprodutibilidade:

| Arquivo | Propósito |
|---------|-----------|
| `triage_results.xlsx` | Resultados completos |
| `protocol.json` | Protocolo com hashes de entrada, configuração e execução |
| `triage_report.txt` | Relatório estatístico |
| `academic_report.md` | Relatório formatado para publicação |
| `config_audit.json` | Configuração completa utilizada |
| `APPENDIX_INDEX.md` | Índice dos artefatos |
| `appendix_manifest.json` | Manifesto de conformidade |

### Reprodutibilidade

Qualquer pessoa com os mesmos arquivos de entrada (`artigos.csv`, `config.json`, `terms.xlsx` ou `terms.csv`) e a mesma versão do FastSLR produzirá **exatamente** os mesmos resultados. O `protocol.json` contém hashes SHA-256 para verificação.

---

## Perfis de Configuração

Salve configurações frequentes como perfis reutilizáveis:

```bash
# Salvar
fastslr profile save revisao-2024 -c config.json -d "Config final da RSL 2024"

# Listar
fastslr profile list

# Carregar
fastslr profile load revisao-2024 -o config.json
```

Perfis são armazenados em `~/.fastslr/profiles/` como arquivos JSON.

---

## Internacionalização

FastSLR suporta três idiomas para a interface:

| Código | Idioma |
|--------|--------|
| `en` | English |
| `pt_BR` | Português (Brasil) |
| `es` | Español |

### Configurar idioma

**Via flag CLI:**
```bash
fastslr run artigos.csv -c config.json -l pt_BR
```

**Via variável de ambiente:**
```bash
export FASTSLR_LANG=pt_BR
fastslr run artigos.csv -c config.json
```

**Detecção automática:** Se nenhum idioma for especificado, o sistema detecta o locale do sistema operacional.

---

## Uso Programático

FastSLR pode ser usado como biblioteca Python:

```python
from fastslr.core import process_articles, collect_statistics
from fastslr.core.config import load_config, parse_terms_csv, load_global_params
from fastslr.core.io import load_table_safe
from fastslr.core.patterns import precompile_patterns
from fastslr.core.normalization import NormalizationEngine

# Carregar dados
config = load_config("config.json")
config = parse_terms_csv("terms.xlsx", config)
df = load_table_safe("artigos.csv")

# Preparar normalizacao e padroes
norm_rules = config.get("normalization_rules", {})
norm_engine = NormalizationEngine(norm_rules)
global_params = load_global_params(config.get("global", {}))

for block in config.get("_domain_blocks", []):
    config[block] = precompile_patterns(config[block], norm_engine, global_params)
    config[block]["normalization_engine"] = norm_engine

# Executar triagem
result_df, stats = process_articles(df, config)

# Resultados
print(f"Total: {stats['total_articles']}")
print(f"Tempo: {stats['processing_time']:.2f}s")
print(f"Distribuicao: {stats['decision_distribution']}")
```

### Via Controller (caminho simplificado)

```python
from pathlib import Path
from fastslr.app.controller import run_triage

result = run_triage(
    input_path=Path("artigos.csv"),
    config_path=Path("config.json"),
    terms_path=Path("terms.xlsx"),
)

print(f"Aprovados: {(result.result_df['Final_Decision'] == 'APPROVED_FINAL').sum()}")
print(f"Sinalizados: {(result.result_df['Final_Decision'] == 'FLAGGED_FINAL').sum()}")
print(f"Rejeitados: {(result.result_df['Final_Decision'] == 'REJECTED_FINAL').sum()}")
```

---

## FAQ

### Quais formatos de entrada são suportados?

CSV (qualquer encoding, separadores `;`, `,` ou `\t`) e XLSX. O sistema detecta automaticamente o formato de exportação do Zotero, Scopus e Web of Science.

### O que acontece se meu CSV não tem a coluna `manual_tags`?

O sistema funciona normalmente. Artigos sem tags recebem um uplift de 17% no score (configurável via `NO_TAGS_UPLIFT`) para compensar a falta de dados.

### Posso usar expressões regulares nos termos?

Sim. Defina `is_regex=1` no CSV de termos. Exemplo: `ML|AI|DL` corresponde a qualquer uma das siglas.

### O que é o `FAIL_FAST_GLOBAL`?

Quando ativado, se um bloco rejeitar o artigo, os blocos seguintes não são avaliados. Isso melhora a performance sem alterar os resultados finais (um bloco rejeitado já garante `REJECTED_FINAL` na política "special").

### Como funciona a "regra especial" de aprovação?

Na política "special", se exatamente 1 bloco estiver FLAGGED (por score, não por anti-termo) e todos os demais estiverem APPROVED com score >= `SPECIAL_APPROVAL_THRESHOLD` (padrão: 40), o artigo é aprovado. Isso evita falsos negativos quando um único bloco está na fronteira.

### Qual preset devo usar?

- **`standard` (5 níveis):** Recomendado para a maioria das RSL. Permite granularidade fina na classificação de termos.
- **`simple` (3 níveis):** Para projetos menores ou com poucos termos.
- **`binary` (1 nível):** Para triagem rápida onde só importa "relevante ou não".

### Como garanto a reprodutibilidade?

1. Use o mesmo `config.json` e `terms.xlsx` ou `terms.csv`
2. Use a mesma versão do FastSLR (`fastslr version`)
3. Inclua o `protocol.json` como material suplementar
4. Os hashes SHA-256 no protocolo permitem verificar que os arquivos de entrada não foram alterados

---

## Licença

MIT
