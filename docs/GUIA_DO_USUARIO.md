# Guia do Usuário — FastSLR

> **Manual completo de uso** · FastSLR v3.0.0 · Triagem determinística universal para Revisões Sistemáticas de Literatura (RSL/SLR)

Este guia ensina, do zero ao resultado publicável, como instalar, configurar e operar o FastSLR para **qualquer** tipo de revisão sistemática — saúde, engenharia, computação, ciências sociais, negócios, educação, etc. Nenhum conhecimento de programação é necessário para o uso básico.

---

## Índice

1. [O que é o FastSLR e quando usar](#1-o-que-é-o-fastslr-e-quando-usar)
2. [Instalação](#2-instalação)
3. [Conceitos fundamentais](#3-conceitos-fundamentais)
4. [Início rápido (5 passos)](#4-início-rápido-5-passos)
5. [Fluxo de trabalho completo](#5-fluxo-de-trabalho-completo)
6. [Preparando seus dados de entrada](#6-preparando-seus-dados-de-entrada)
7. [Criando o arquivo de termos](#7-criando-o-arquivo-de-termos)
8. [Configurando o `config.json`](#8-configurando-o-configjson)
9. [Referência completa de comandos (CLI)](#9-referência-completa-de-comandos-cli)
10. [Interface interativa (TUI)](#10-interface-interativa-tui)
11. [Interpretando os resultados](#11-interpretando-os-resultados)
12. [Calibração e ajuste fino](#12-calibração-e-ajuste-fino)
13. [Reprodutibilidade e pacote acadêmico](#13-reprodutibilidade-e-pacote-acadêmico)
14. [Idiomas (internacionalização)](#14-idiomas-internacionalização)
15. [Uso programático (API Python)](#15-uso-programático-api-python)
16. [Receitas por tipo de SLR](#16-receitas-por-tipo-de-slr)
17. [Resolução de problemas (Troubleshooting)](#17-resolução-de-problemas-troubleshooting)
18. [Glossário](#18-glossário)

---

## 1. O que é o FastSLR e quando usar

O FastSLR automatiza a fase de **triagem (screening)** de uma RSL: avaliar centenas ou milhares de artigos contra seus critérios de inclusão/exclusão. Ele é **100% determinístico** — não usa inteligência artificial, *machine learning* nem correspondência aproximada. Toda decisão é baseada em **regras explícitas** (termos de busca organizados por relevância), o que garante três propriedades essenciais para publicação:

| Propriedade | O que significa |
|---|---|
| **Reproduzível** | Mesma entrada + mesma configuração + mesma versão → **exatamente** o mesmo resultado. |
| **Auditável** | Cada decisão vem com uma justificativa (`Decision_Reason`) e os termos encontrados ficam destacados. |
| **Transparente** | A lógica é configuração legível (`config.json` + `terms.csv`), não um modelo opaco. |

**Use o FastSLR quando** você precisa triar muitos registros bibliográficos de forma rápida, consistente e documentável — e quer poder anexar a metodologia computacional como material suplementar do seu artigo.

**O FastSLR não substitui** o julgamento humano: artigos na fronteira são marcados como `FLAGGED_FINAL` justamente para revisão manual. Ele acelera e padroniza, não decide sozinho o que entra na sua revisão.

---

## 2. Instalação

### Requisitos

- **Python 3.10 ou superior**. Verifique com `python --version`.

### Instalação via pip

```bash
pip install fastslr
```

Confirme a instalação:

```bash
fastslr version
```

> Em alguns sistemas o comando pode ser invocado como `python -m fastslr` em vez de `fastslr`. Ambos funcionam.

### Dependência opcional (detecção de encoding)

Para detecção automática de codificação em CSVs problemáticos:

```bash
pip install "fastslr[chardet]"
```

Isto é **opcional**: o FastSLR já tenta automaticamente uma cadeia de codificações (`utf-8-sig → utf-8 → cp1252 → latin-1`), então arquivos exportados de Excel/Scopus/Web of Science em codificações europeias carregam mesmo sem o `chardet`.

### Instalação para desenvolvimento

```bash
git clone https://github.com/Lharden/fastslr.git
cd fastslr
pip install -e ".[dev]"
```

---

## 3. Conceitos fundamentais

Entender estes cinco conceitos é suficiente para usar o FastSLR com confiança.

### 3.1 Blocos de domínio

Um **bloco** é uma dimensão temática da sua revisão. Você define quantos quiser, com os nomes que quiser. Um artigo precisa "passar" nos blocos relevantes para ser incluído.

> **Exemplo** (RSL sobre "Machine Learning em Cadeia de Suprimentos"):
> | Bloco | O que avalia |
> |---|---|
> | `CTX` (Contexto) | O artigo é sobre cadeia de suprimentos? |
> | `TECH` (Tecnologia) | O artigo usa machine learning? |
> | `APP` (Aplicação) | O artigo aborda uma aplicação concreta? |

### 3.2 Níveis de importância (1 a 5)

Cada termo **positivo** recebe um nível: **1 = essencial**, **5 = tangencial**. O nível define quantos pontos o termo vale.

| Nível | Significado | Pontos (padrão) |
|---|---|---|
| 1 | Essencial / exato | 10 |
| 2 | Muito relevante | 8 |
| 3 | Relevante | 6 |
| 4 | Parcialmente relevante | 4 |
| 5 | Tangencial | 2 |

### 3.3 Tipos de termo

| Tipo | Sigla | Efeito |
|---|---|---|
| **Positivo** | `pos` | Contribui para a pontuação do bloco. |
| **Anti-exclusão** | `anti` | Se encontrado, **rejeita** o artigo naquele bloco imediatamente. |
| **Anti-sinalização** | `flag` | Se encontrado, **rebaixa** um `APPROVED` para `FLAGGED`. |

### 3.4 Pré-triagem global (T0)

O **T0** é um filtro aplicado **antes** dos blocos, usando apenas anti-termos globais. Serve para descartar de imediato o que está obviamente fora do escopo (ex.: `book review`, `editorial`, `retracted`). Se o T0 rejeita um artigo, nenhum bloco é avaliado. O T0 é **opcional**.

### 3.5 Decisões finais

| Decisão | Significado | Ação recomendada |
|---|---|---|
| `APPROVED_FINAL` | Relevante | Incluir na revisão |
| `FLAGGED_FINAL` | Fronteira | **Revisão manual** |
| `REJECTED_FINAL` | Fora do escopo | Excluir |

---

## 4. Início rápido (5 passos)

### Passo 1 — Crie um projeto

```bash
fastslr new-project minha-rsl --blocks "CTX,TECH,APP" --preset standard
```

Isto cria a pasta `minha-rsl/` com:
- `config.json` — configuração pronta para uso;
- `terms.xlsx` — planilha de termos para você preencher;
- `terms.csv` — cópia em texto (útil para versionamento/scripts).

> Se a pasta já existir, o comando **se recusa a sobrescrever** (para proteger seu trabalho). Use `--force` apenas se quiser realmente recriar do zero.

### Passo 2 — Preencha seus termos

Abra `minha-rsl/terms.xlsx` (ou `terms.csv`) e adicione os termos de busca de cada bloco. Veja a [Seção 7](#7-criando-o-arquivo-de-termos) para o formato detalhado. Exemplo mínimo:

```
block;kind;term;level;section_scope;is_regex;normalization_type;normalization_target
CTX;pos;supply chain;1;any;0;;
TECH;pos;machine learning;1;any;0;;
TECH;pos;deep learning;2;any;0;;
APP;pos;optimization;3;any;0;;
GLOBAL;anti;book review;;any;0;;
```

### Passo 3 — Verifique o setup (`doctor`)

```bash
fastslr doctor --input artigos.csv --config minha-rsl/config.json --terms minha-rsl/terms.xlsx
```

O `doctor` mostra: quais colunas foram detectadas no seu CSV, quantos termos válidos por bloco, eventuais avisos e o **comando exato** de execução. **Sempre rode o `doctor` antes da triagem.**

### Passo 4 — Execute a triagem

```bash
fastslr run artigos.csv --config minha-rsl/config.json --terms minha-rsl/terms.xlsx
```

### Passo 5 — Confira os resultados

Os arquivos aparecem em `output/` (ao lado do seu CSV de entrada):
- `triage_results.xlsx` — resultados completos com scores, status e termos destacados;
- `triage_report.txt` — estatísticas;
- `academic_package.zip` — pacote pronto para o material suplementar.

---

## 5. Fluxo de trabalho completo

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│ PREPARAÇÃO  │ → │ CALIBRAÇÃO  │ → │  EXECUÇÃO   │ → │ DOCUMENTAÇÃO│
└─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘
 export do        preview +          run completo      pacote
 gerenciador,     coverage,          + revisão dos      acadêmico,
 new-project,     ajuste de          FLAGGED            protocol.json
 termos           termos/limiares    manualmente        no artigo
```

### Etapa 1 — Preparação
1. Exporte seus artigos do gerenciador (Zotero, Scopus, Web of Science) em CSV/XLSX.
2. `fastslr new-project minha-rsl -b "CTX,TECH,APP"`.
3. Preencha `terms.xlsx`.

### Etapa 2 — Calibração
4. `fastslr doctor --input artigos.csv -c config.json -t terms.xlsx`.
5. `fastslr preview artigos.csv -c config.json -t terms.xlsx -s 100` — roda numa amostra para inspeção rápida.
6. Analise a distribuição de decisões. Muitos `FLAGGED`? Muitos `REJECTED`? Ajuste (ver [Seção 12](#12-calibração-e-ajuste-fino)).
7. `fastslr coverage artigos.csv -c config.json -t terms.xlsx` — identifica termos mortos (0 matches) e amplos demais.
8. Remova termos mortos, refine os amplos demais; repita até a amostra fazer sentido.

### Etapa 3 — Execução
9. `fastslr run artigos.csv -c config.json -t terms.xlsx`.
10. Abra `triage_results.xlsx` e revise **manualmente** os `FLAGGED_FINAL`.
11. Documente suas decisões manuais.

### Etapa 4 — Documentação
12. Inclua o `protocol.json` (dentro do `academic_package.zip`) como material suplementar.
13. Cite a versão do FastSLR (`fastslr version`) e o `config_hash` para garantir reprodutibilidade.

### Etapa 5 — Iteração (se necessário)
14. Ajuste termos/limiares e re-execute.
15. `fastslr diff resultado_v1.xlsx resultado_v2.xlsx` — mostra o que mudou entre as versões.

---

## 6. Preparando seus dados de entrada

### Formatos aceitos

- **CSV** em qualquer codificação comum, com separador `;`, `,` ou tabulação — detectados automaticamente.
- **XLSX** (Excel).

### Gerenciadores reconhecidos

O FastSLR detecta e mapeia automaticamente as colunas de exportações do **Zotero**, **Scopus** e **Web of Science**, além de variações comuns. As quatro informações que ele procura:

| Campo interno | Nomes reconhecidos (exemplos) |
|---|---|
| `id` | Key, ID, EID, UT, Record ID |
| `title` | Title, TI, Article Title, Título |
| `abstract` | Abstract Note, Abstract, AB, Resumo, Resumen |
| `manual_tags` | Manual Tags, Tags, Author Keywords, Keywords, DE, Palavras-chave |

O reconhecimento é **tolerante a maiúsculas/minúsculas e a acentos**. Se sua coluna tiver um nome diferente, basta mapeá-la no `config.json` (ver [Seção 8](#8-configurando-o-configjson)).

> **Sem coluna de palavras-chave?** Sem problema. Artigos sem `manual_tags` recebem um pequeno *uplift* (multiplicador) na pontuação para compensar a falta de dados (configurável via `NO_TAGS_UPLIFT`, padrão 1.17).

### Dica de codificação (encoding)
Se você exportou do Excel em um sistema em português/espanhol, o arquivo pode estar em `cp1252`/`latin-1`. O FastSLR lida com isso automaticamente. Se mesmo assim houver erro, salve o CSV como **UTF-8** no Excel ("Salvar como → CSV UTF-8".

---

## 7. Criando o arquivo de termos

O arquivo de termos é o coração da sua triagem. O formato é o mesmo em `.xlsx` e em `.csv` (com separador `;`).

### 7.1 Estrutura das colunas

```
block;kind;term;level;section_scope;is_regex;normalization_type;normalization_target
```

| Coluna | Obrigatória | Valores | Descrição |
|---|---|---|---|
| `block` | **Sim** | nome do bloco ou `GLOBAL` | A que bloco o termo pertence. `GLOBAL` → pré-triagem T0. |
| `kind` | **Sim** | `pos` / `anti` / `flag` | Tipo do termo. |
| `term` | **Sim** | texto livre | O termo de busca. |
| `level` | Só para `pos` | `1` a `5` | Nível de importância (1 = essencial). |
| `section_scope` | Não | `any` / `title` / `abstract` / `manual_tags` | Onde buscar (padrão `any` = todas). |
| `is_regex` | Não | `0` / `1` | Tratar `term` como expressão regular. |
| `normalization_type` | Não | `abbreviation` / `compound_variant` / `symbol_replacement` | Regra de normalização (ver 7.5). |
| `normalization_target` | Não | texto | A forma normalizada de destino. |

### 7.2 Termos positivos, anti e flag

```csv
# Positivos: contribuem para a pontuação
TECH;pos;machine learning;1;any;0;;
TECH;pos;deep learning;1;any;0;;
TECH;pos;neural network;2;any;0;;

# Anti-exclusão: rejeitam o bloco se encontrados
TECH;anti;systematic review;;any;0;;
TECH;anti;literature review;;any;0;;

# Anti-sinalização: rebaixam APPROVED → FLAGGED
CTX;flag;conference abstract;;any;0;;

# Globais (T0): aplicados antes de tudo
GLOBAL;anti;book review;;any;0;;
GLOBAL;anti;retracted;;any;0;;
GLOBAL;flag;editorial;;any;0;;
```

### 7.3 Curingas (wildcards)

Use `*` para casar qualquer sequência de caracteres:

```csv
TECH;pos;optim*;3;any;0;;     # casa optimize, optimization, optimal...
CTX;pos;sustainab*;2;any;0;;  # casa sustainable, sustainability...
```

### 7.4 Expressões regulares (regex)

Ative `is_regex=1` para usar regex completa. Útil para siglas e alternativas:

```csv
TECH;pos;ML|AI|DL;2;title;1;;            # casa ML, AI ou DL no título
CTX;pos;IoT|internet of things;1;any;1;; # sigla ou forma extensa
```

> O FastSLR casa termos com **fronteiras de palavra inteligentes**: termos técnicos com símbolos como `C++`, `C#`, `.NET` e `F#` são casados corretamente (sem precisar de regex).

### 7.5 Termos compostos (proximidade)

Termos contendo `and`, `&`, `or` ou `/` são automaticamente expandidos em **busca por proximidade bidirecional**:

```csv
CTX;pos;oil and gas;1;any;0;;   # casa "oil ... gas" OU "gas ... oil" com poucas palavras entre eles
TECH;pos;input/output;2;any;0;;
```

A "distância" máxima entre os componentes é controlada por `MAX_GAP_BETWEEN_TERMS` no `config.json` (padrão 2 palavras).

### 7.6 Normalização (abreviaturas, variantes, símbolos)

Unifica variações para que **um único termo** capture várias formas escritas:

```csv
# Abreviatura → forma extensa
TECH;pos;AI;1;any;0;abbreviation;artificial intelligence

# Variante composta (hífen/junção) → forma canônica
CTX;pos;supply-chain;2;any;0;compound_variant;supply chain

# Substituição de símbolo
TECH;pos;c#;1;any;0;symbol_replacement;csharp
```

### 7.7 Boas práticas para termos

- **Comece amplo, depois refine** com o comando `coverage`.
- **Nível 1** apenas para o essencial; reserve níveis 4–5 para termos tangenciais.
- **Cubra sinônimos e variantes** (singular/plural, BrE/AmE, sigla/extenso).
- **Use `anti` com parcimônia**: um anti-termo rejeita o bloco inteiro.
- Um termo positivo cujo nível esteja **fora dos níveis configurados** vale 0 pontos e leva o bloco a `REJECTED` — então mantenha os níveis coerentes com o `config.json`.

---

## 8. Configurando o `config.json`

O `config.json` controla todo o comportamento do motor. Estrutura geral:

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

### 8.1 Parâmetros globais (`global`)

| Chave | Padrão | Descrição |
|---|---|---|
| `DECISION_POLICY` | `"special"` | Política de decisão final: `special`, `strict` ou `k_of_n` (ver 8.4). |
| `PONTUACAO_NIVEIS` | `{1:10…5:2}` | Pontos atribuídos a cada nível. |
| `LIMITES_APROVADO` | `{1:10,2:12,3:18,4:22,5:null}` | Score mínimo para `APPROVED`, por nível. `null` = nunca aprova só por score. |
| `LIMITES_SINALIZADO` | `{1:6,2:6,3:6,4:7,5:12}` | Score mínimo para `FLAGGED`, por nível. |
| `WEIGHTS` | `{title:2.0, abstract:1.0, manual_tags:1.5}` | Peso de cada seção no cálculo. |
| `NO_TAGS_UPLIFT` | `1.17` | Multiplicador quando o artigo não tem palavras-chave. |
| `MAX_SECTION_SCORE` | `30` | Teto de pontos por seção (antes do peso). |
| `FAIL_FAST_GLOBAL` | `true` | Se um bloco rejeita, pula os blocos seguintes (otimização). |
| `ENABLE_PROXIMITY_DETECTION` | `true` | Detecta termos compostos automaticamente. |
| `MAX_GAP_BETWEEN_TERMS` | `2` | Palavras máximas entre componentes de termo composto. |
| `NOISE_PROFILE` | `"relaxed"` | `relaxed` ou `strict` (ativa filtros de ruído — ver 8.3). |
| `ERROR_POLICY` | `"flag"` | `flag` (marca artigo com erro como `FLAGGED`) ou `fail` (aborta). |
| `MAX_ERROR_RATE` | `0.05` | Aborta a execução se a taxa de erro exceder isto (5%). |

### 8.2 Parâmetros avançados (opcionais)

| Chave | Padrão | Descrição |
|---|---|---|
| `ENABLE_SPECIAL_APPROVAL_RULE` | `true` | Liga/desliga a regra especial da política `special`. |
| `SPECIAL_APPROVAL_THRESHOLD` | `40.0` | Score mínimo dos blocos aprovados para a regra especial valer. |
| `MIN_APPROVED_BLOCKS` | — | Política `k_of_n`: nº mínimo de blocos aprovados. |
| `MAX_FLAGGED_BLOCKS_FOR_APPROVAL` | `0` | Política `k_of_n`: nº máximo de blocos sinalizados tolerado. |
| `BLOCK_ORDER` | — | Lista que fixa a ordem de avaliação dos blocos. |
| `LEVEL_ORDER` | `[1,2,3,4,5]` | Ordem dos níveis. |
| `TOKEN_UNIT_FOR_GAPS` | `\S+` | Fragmento regex que define "uma palavra" na proximidade (avançado). |

### 8.3 Filtros de ruído (`NOISE_PROFILE: "strict"`)

Quando `NOISE_PROFILE` é `"strict"`, exige-se evidência mais robusta para aprovar um bloco:

| Chave | Padrão | Efeito |
|---|---|---|
| `MIN_UNIQUE_TERMS_FOR_APPROVAL` | `1` | Mínimo de termos únicos casados. |
| `MIN_SECTIONS_WITH_HITS_FOR_APPROVAL` | `1` | Mínimo de seções com pelo menos um match. |
| `REQUIRE_NON_WEAK_TERM_FOR_APPROVAL` | `false` | Exige ao menos um termo não-"fraco". |
| `WEAK_LEVELS` | `[5]` | Quais níveis são considerados "fracos". |

> Use `strict` quando estiver recebendo muitos falsos positivos (artigos aprovados por um único termo fraco). Use `relaxed` (padrão) para maximizar o recall.

### 8.4 Políticas de decisão

**`special` (padrão, recomendada).** Qualquer bloco rejeitado → artigo rejeitado. Possui uma **regra especial**: se exatamente **1** bloco está `FLAGGED` por score, **e há pelo menos um outro bloco aprovado**, e **todos** os aprovados têm score ≥ `SPECIAL_APPROVAL_THRESHOLD`, o artigo é aprovado (evita perder artigos fortes que ficaram na fronteira em uma única dimensão).

**`strict`.** Todos os blocos devem ser `APPROVED` para aprovar o artigo. Maximiza precisão.

**`k_of_n`.** Pelo menos `MIN_APPROVED_BLOCKS` blocos aprovados, com no máximo `MAX_FLAGGED_BLOCKS_FOR_APPROVAL` sinalizados, e nenhum rejeitado.

### 8.5 Mapeamento de colunas (`fields`)

Se as colunas do seu CSV não forem reconhecidas automaticamente, mapeie-as:

```json
"fields": {
  "id": "Key",
  "title": "Title",
  "abstract": "Abstract Note",
  "manual_tags": "Author Keywords"
}
```

### 8.6 Saída (`output`)

```json
"output": { "csv": false, "xlsx": true, "academic_package": true }
```
Controla quais formatos são gerados. `academic_package` gera o ZIP de reprodutibilidade.

### 8.7 Presets de nível (no `new-project`)

| Preset | Níveis | Quando usar |
|---|---|---|
| `binary` | 1 | Triagem rápida: relevante ou não. |
| `simple` | 3 | Projetos menores ou poucos termos. |
| `standard` | 5 | **Recomendado** — granularidade fina (padrão). |

---

## 9. Referência completa de comandos (CLI)

Todos os comandos aceitam `--lang/-l` (`en`, `pt_BR`, `es`).

### `fastslr version`
Mostra a versão instalada.

### `fastslr doctor` — verificar o setup
```bash
fastslr doctor --input artigos.csv -c config.json -t terms.xlsx [-o output/] [-l pt_BR]
```
| Flag | Descrição |
|---|---|
| `-i, --input` | CSV/XLSX de artigos. |
| `-c, --config` | Caminho do `config.json`. |
| `-t, --terms` | Caminho do `terms.xlsx`/`terms.csv`. |
| `-o, --output` | Diretório de saída sugerido. |

Mostra colunas detectadas, blocos carregados, contagem de termos válidos, avisos e o comando de `run` exato. **Rode antes de toda triagem.**

### `fastslr run` — executar a triagem
```bash
fastslr run artigos.csv -c config.json -t terms.xlsx [-o output/] [-l pt_BR] [-q] [-y]
```
| Flag | Descrição |
|---|---|
| `-c, --config` | **(obrigatório)** `config.json`. |
| `-t, --terms` | `terms.xlsx`/`terms.csv`. |
| `-o, --output` | Diretório de saída (padrão: `output/` ao lado do input). |
| `-q, --quiet` | Suprime a saída no terminal. |
| `-y, --yes` | Prossegue mesmo havendo avisos de configuração (sem perguntar). |

> Em execução **não-interativa** (pipe, CI, agendador), o `run` prossegue automaticamente sem travar esperando confirmação. Use `--yes` para forçar isso explicitamente.

### `fastslr preview` — pré-visualizar numa amostra
```bash
fastslr preview artigos.csv -c config.json -t terms.xlsx [-s 50]
```
| Flag | Descrição |
|---|---|
| `-s, --sample` | Tamanho da amostra (padrão 50; **mínimo 1**). |

### `fastslr coverage` — análise de cobertura
```bash
fastslr coverage artigos.csv -c config.json -t terms.xlsx [-o cobertura.csv]
```
Identifica **termos mortos** (0 matches), **termos amplos demais** (>80% dos artigos) e blocos sem poder de discriminação.

### `fastslr diff` — comparar duas execuções
```bash
fastslr diff resultado_v1.xlsx resultado_v2.xlsx
```
Mostra os artigos cuja decisão mudou entre as versões. Artigos presentes em apenas um dos arquivos aparecem como `MISSING`.

### `fastslr new-project` — criar novo projeto
```bash
fastslr new-project minha-rsl -b "CTX,TECH,APP" [-p standard] [-o dir/] [--force]
```
| Flag | Descrição |
|---|---|
| `-b, --blocks` | **(obrigatório)** nomes dos blocos separados por vírgula. |
| `-p, --preset` | `binary` / `simple` / `standard` (padrão). |
| `-o, --output` | Diretório de saída. |
| `--force` | Sobrescreve um projeto existente (cuidado: apaga edições). |

### `fastslr export` — (re)gerar o pacote acadêmico
```bash
fastslr export resultado.xlsx [-o output/] [-c config.json]
```

### `fastslr terms` — navegar pelos termos configurados
```bash
fastslr terms -c config.json -t terms.xlsx [-b TECH] [-k pos]
```
| Flag | Descrição |
|---|---|
| `-b, --block` | Filtrar por bloco. |
| `-k, --kind` | Filtrar por tipo (`pos`/`anti`/`flag`). |

### `fastslr profile` — gerenciar perfis de configuração
```bash
fastslr profile save meu-perfil -c config.json -d "Config final da RSL 2026"
fastslr profile load meu-perfil -o config.json
fastslr profile list
```
Perfis são salvos em `~/.fastslr/profiles/`. Os nomes são sanitizados automaticamente (não é possível usar caminhos como `../`).

### `fastslr tui` — interface interativa
```bash
fastslr tui
```

---

## 10. Interface interativa (TUI)

Para quem prefere uma interface guiada no terminal:

```bash
fastslr tui
```

| Tela | Função |
|---|---|
| New Project | Criar projeto com preset |
| Load Profile | Carregar configuração salva |
| Edit Configuration | Ajustar limiares e parâmetros |
| Browse Terms | Visualizar/filtrar termos por bloco |
| Run Triage | Executar com barra de progresso |
| Results Explorer | Navegar resultados |
| Coverage Analysis | Analisar cobertura de termos |
| Compare Runs | Comparar duas execuções |
| Export Package | Gerar pacote acadêmico |
| Settings & Language | Configurar idioma |

---

## 11. Interpretando os resultados

### Colunas de `triage_results.xlsx`

| Coluna | Descrição |
|---|---|
| `ID` | Identificador do artigo. |
| `Title_Highlighted` / `Abstract_Highlighted` / `Tags_Highlighted` | Texto com os termos encontrados marcados como `***TERMO***`. |
| `RawScore_<BLOCO>` | Pontuação bruta do bloco. |
| `FinalScore_<BLOCO>` | Pontuação final (após *uplift*). |
| `BestLevel_<BLOCO>` | Melhor nível encontrado no bloco. |
| `Status_<BLOCO>` | `APPROVED` / `FLAGGED` / `REJECTED` / `NOT_EVALUATED`. |
| `Highlights_<BLOCO>` | Detalhe dos matches positivos. |
| `AntiHighlights_<BLOCO>` | Anti-termos de exclusão encontrados. |
| `Flags_<BLOCO>` | Anti-termos de sinalização encontrados. |
| `Final_Decision` | `APPROVED_FINAL` / `FLAGGED_FINAL` / `REJECTED_FINAL`. |
| `Decision_Reason` | Justificativa textual da decisão (auditável). |
| `Status_T0` etc. | Resultado da pré-triagem global (se configurada). |

### Como ler

- **Score alto + APPROVED** → claramente relevante.
- **Score moderado + FLAGGED** → fronteira; **revise manualmente**.
- **REJECTED por anti-termo** → excluído por exclusão, independentemente do score (veja `AntiHighlights`).
- **REJECTED "No positive terms found"** → nenhum termo do bloco apareceu.
- **Score 0 → REJECTED** → não há evidência pontuável; o artigo não entra na fila de revisão.

---

## 12. Calibração e ajuste fino

A calibração é iterativa. Use `preview` (rápido, numa amostra) e `coverage` para guiar os ajustes.

| Sintoma | Provável causa | Ação |
|---|---|---|
| **Muitos `FLAGGED`** | Limiares de aprovação altos demais | Reduza `LIMITES_APROVADO` ou suba o peso do título. |
| **Muitos `REJECTED`** | Termos cobrem poucos sinônimos | Adicione variantes; cheque `coverage` por termos mortos. |
| **Poucos `REJECTED` (quase tudo passa)** | Termos amplos demais | Veja `coverage` (termos >80%); restrinja `section_scope` ou suba o nível. |
| **Falsos positivos por 1 termo fraco** | Perfil de ruído relaxado | Use `NOISE_PROFILE: "strict"` + `MIN_UNIQUE_TERMS_FOR_APPROVAL`. |
| **Scores inesperados** | Termo casando onde não devia | Inspecione a coluna `Highlights` para ver o que casou. |

**Termos mortos** (0 matches) só adicionam ruído — remova-os. **Termos amplos demais** (casam quase tudo) não discriminam — torne-os mais específicos ou suba o nível.

---

## 13. Reprodutibilidade e pacote acadêmico

Quando `output.academic_package = true`, o FastSLR gera `academic_package.zip` com tudo necessário para reprodutibilidade:

| Arquivo | Propósito |
|---|---|
| `triage_results.xlsx` | Resultados completos. |
| `protocol.json` | Protocolo com hashes SHA-256 de entrada/config/execução. |
| `triage_report.txt` | Relatório estatístico. |
| `academic_report.md` | Relatório formatado para publicação. |
| `config_audit.json` | Configuração completa utilizada. |
| `APPENDIX_INDEX.md` | Índice dos artefatos. |
| `appendix_manifest.json` | Manifesto de conformidade. |

### Como garantir (e provar) reprodutibilidade

1. Use o mesmo `config.json`, `terms.csv`/`terms.xlsx` e a **mesma versão** do FastSLR.
2. Inclua o `protocol.json` como **material suplementar** do artigo.
3. Os **hashes SHA-256** no protocolo permitem que qualquer revisor verifique que os arquivos de entrada não foram alterados.
4. Rodar a mesma entrada duas vezes produz resultados **idênticos** nos dados de triagem (apenas metadados voláteis como `run_timestamp` e `execution_id` diferem).

### Como citar a metodologia (modelo)
> "A triagem foi realizada com FastSLR v3.0.0, uma ferramenta de filtragem determinística baseada em regras. Os critérios (blocos de domínio, níveis de relevância e limiares) estão documentados no `config.json` e `terms.csv` fornecidos como material suplementar. O `protocol.json` contém os hashes SHA-256 que garantem a reprodutibilidade do processo."

---

## 14. Idiomas (internacionalização)

A interface está disponível em três idiomas (os **dados de saída permanecem em inglês** para garantir reprodutibilidade entre locales):

| Código | Idioma |
|---|---|
| `en` | English |
| `pt_BR` | Português (Brasil) |
| `es` | Español |

```bash
# Via flag
fastslr run artigos.csv -c config.json -l pt_BR

# Via variável de ambiente
export FASTSLR_LANG=pt_BR    # Windows (PowerShell): $env:FASTSLR_LANG="pt_BR"
fastslr run artigos.csv -c config.json
```
Sem especificar, o idioma é detectado a partir do sistema operacional.

---

## 15. Uso programático (API Python)

### Caminho simplificado (controller)

```python
from pathlib import Path
from fastslr.app.controller import run_triage

result = run_triage(
    input_path=Path("artigos.csv"),
    config_path=Path("config.json"),
    terms_path=Path("terms.xlsx"),
)

df = result.result_df
print("Aprovados:", (df["Final_Decision"] == "APPROVED_FINAL").sum())
print("Sinalizados:", (df["Final_Decision"] == "FLAGGED_FINAL").sum())
print("Rejeitados:", (df["Final_Decision"] == "REJECTED_FINAL").sum())
```

### Caminho de baixo nível (motor)

```python
from fastslr.core import process_articles, collect_statistics
from fastslr.core.config import load_config, parse_terms_csv, load_global_params
from fastslr.core.io import load_table_safe
from fastslr.core.patterns import precompile_patterns
from fastslr.core.normalization import NormalizationEngine

config = load_config("config.json")
config = parse_terms_csv("terms.xlsx", config)
df = load_table_safe("artigos.csv")

norm_engine = NormalizationEngine(config.get("normalization_rules", {}))
global_params = load_global_params(config.get("global", {}))
for block in config.get("_domain_blocks", []):
    config[block] = precompile_patterns(config[block], norm_engine, global_params)
    config[block]["normalization_engine"] = norm_engine

result_df, stats = process_articles(df, config)
print(f"Total: {stats['total_articles']} em {stats['processing_time']:.2f}s")
print("Distribuição:", stats["decision_distribution"])
```

---

## 16. Receitas por tipo de SLR

O FastSLR é **agnóstico de domínio**. Os exemplos abaixo mostram como os mesmos mecanismos servem a áreas muito diferentes — basta mudar os blocos e termos.

### 16.1 Saúde / Medicina — "Telemedicina para diabetes"
Blocos: `COND` (condição), `INTERV` (intervenção), `OUTCOME` (desfecho).
```csv
block;kind;term;level;section_scope;is_regex;normalization_type;normalization_target
COND;pos;diabetes;1;any;0;;
COND;pos;diabetic;2;any;0;;
INTERV;pos;telemedicine;1;any;0;;
INTERV;pos;telehealth;1;any;0;;
INTERV;pos;mhealth;2;any;0;abbreviation;mobile health
OUTCOME;pos;glycemic control;1;any;0;;
OUTCOME;pos;hba1c;1;any;0;;
GLOBAL;anti;animal model;;any;0;;
GLOBAL;anti;in vitro;;any;0;;
```

### 16.2 Engenharia — "Manutenção preditiva industrial"
Blocos: `CTX` (contexto industrial), `METHOD` (método), `DATA` (dados).
```csv
CTX;pos;manufacturing;1;any;0;;
CTX;pos;industrial equipment;2;any;0;;
METHOD;pos;predictive maintenance;1;any;0;;
METHOD;pos;condition monitoring;2;any;0;;
METHOD;pos;remaining useful life;1;any;0;abbreviation;rul
DATA;pos;sensor data;2;any;0;;
DATA;pos;vibration analysis;3;any;0;;
GLOBAL;anti;review;;title;0;;
```

### 16.3 Computação — "Detecção de fake news com NLP"
Blocos: `PROB` (problema), `TECH` (técnica).
```csv
PROB;pos;fake news;1;any;0;;
PROB;pos;misinformation;1;any;0;;
PROB;pos;disinformation;2;any;0;;
TECH;pos;NLP|natural language processing;1;any;1;;
TECH;pos;deep learning;1;any;0;;
TECH;pos;transformer;2;any;0;;
TECH;pos;BERT;2;any;0;;
GLOBAL;anti;survey;;title;0;;
```

### 16.4 Ciências Sociais / Educação — "Gamificação no ensino superior"
Blocos: `CTX` (contexto educacional), `INTERV` (gamificação), `POP` (população).
```csv
CTX;pos;higher education;1;any;0;;
CTX;pos;university;2;any;0;;
INTERV;pos;gamification;1;any;0;;
INTERV;pos;game-based learning;1;any;0;compound_variant;game based learning
INTERV;pos;serious games;2;any;0;;
POP;pos;undergraduate;2;any;0;;
POP;pos;student;3;any;0;;
GLOBAL;flag;editorial;;any;0;;
```

> **Princípio comum:** estruture sua pergunta de pesquisa em **dimensões independentes** (ex.: PICO em saúde, Contexto-Método-Dados em engenharia), crie um bloco por dimensão e exija que o artigo passe em todas as dimensões relevantes.

---

## 17. Resolução de problemas (Troubleshooting)

| Problema | Causa provável | Solução |
|---|---|---|
| **"Arquivo não encontrado"** | Caminho errado | Confira o caminho; rode `fastslr doctor` primeiro. |
| **Colunas não detectadas** | Nomes de coluna incomuns | Mapeie em `fields` no `config.json`; veja o que o `doctor` detectou. |
| **Erro de codificação / acentos errados** | CSV em codificação incomum | Geralmente resolvido automaticamente; se persistir, salve como "CSV UTF-8" no Excel. |
| **Tudo vira `REJECTED`** | Termos não casam o vocabulário do corpus | Use `coverage` para ver termos mortos; adicione sinônimos; cheque o `section_scope`. |
| **Tudo vira `APPROVED`/`FLAGGED`** | Termos amplos demais | `coverage` mostra termos >80%; restrinja ou suba o nível; considere `NOISE_PROFILE: strict`. |
| **`run` pede confirmação e não há ninguém** | Execução não-interativa com avisos | Já prossegue sozinho; use `--yes` para explicitar, ou `--quiet`. |
| **`new-project` recusou criar** | A pasta já existe | Use outro nome ou `--force` (apaga o conteúdo). |
| **Corpus vazio gera "0 artigos"** | CSV só com cabeçalho | Confira a exportação do gerenciador; o FastSLR avisa quando a entrada tem 0 linhas. |
| **Resultados diferentes entre máquinas** | Versões diferentes do FastSLR | Padronize a versão (`fastslr version`); a triagem é determinística para a mesma versão. |
| **Taxa de erro alta aborta a execução** | Muitas linhas malformadas | Limpe o CSV; ou ajuste `MAX_ERROR_RATE`/`ERROR_POLICY` no config. |

Para diagnósticos detalhados, **comece sempre pelo `fastslr doctor`** — ele aponta a maioria dos problemas antes da execução.

---

## 18. Glossário

| Termo | Definição |
|---|---|
| **RSL / SLR** | Revisão Sistemática de Literatura. |
| **Triagem / Screening** | Avaliar artigos contra critérios de inclusão/exclusão. |
| **Bloco de domínio** | Dimensão temática da revisão (ex.: Contexto, Tecnologia). |
| **Nível** | Importância de um termo positivo: 1 (essencial) a 5 (tangencial). |
| **T0** | Pré-triagem global por anti-termos, antes dos blocos. |
| **`pos` / `anti` / `flag`** | Termo positivo / anti-exclusão / anti-sinalização. |
| **Proximidade** | Busca de termos compostos ("oil and gas") em qualquer ordem, com folga de palavras. |
| **Normalização** | Unificar variações (abreviaturas, hífens, símbolos) antes da busca. |
| **Uplift** | Multiplicador aplicado a artigos sem palavras-chave. |
| **APPROVED/FLAGGED/REJECTED_FINAL** | Decisão final: incluir / revisar manualmente / excluir. |
| **`protocol.json`** | Arquivo de reprodutibilidade com hashes SHA-256. |
| **`config_hash`** | Hash que identifica unicamente uma configuração. |
| **Determinístico** | Mesma entrada + config + versão → exatamente o mesmo resultado. |

---

*FastSLR é software livre sob licença MIT. Para a arquitetura interna e o algoritmo em detalhe, consulte o `vault/` (documentação técnica) e `docs/TECHNICAL.md`.*
