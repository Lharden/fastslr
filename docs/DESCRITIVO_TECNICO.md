# Descritivo Tecnico do Programa de Computador

## FastSLR -- Motor Deterministico de Triagem para Revisoes Sistematicas da Literatura

---

## 1. Identificacao

| Campo                        | Informacao                                                                                      |
|------------------------------|-------------------------------------------------------------------------------------------------|
| **Titulo do programa**       | FastSLR -- Motor Deterministico de Triagem para Revisoes Sistematicas da Literatura             |
| **Versao**                   | 3.0.0                                                                                           |
| **Autor**                    | Leonardo Harden                                                                                 |
| **Instituicao**              | Pontificia Universidade Catolica do Parana (PUCPR)                                              |
| **Programa de Pos-Graduacao**| Mestrado em Gestao de Cooperativas                                                              |
| **Linguagem de programacao** | Python 3.10+                                                                                    |
| **Licenca**                  | MIT (codigo aberto)                                                                             |
| **Repositorio**              | https://github.com/Lharden/fastslr                                                             |
| **Distribuicao**             | PyPI (`pip install fastslr`)                                                                    |
| **Data de criacao**          | Janeiro 2026                                                                                    |
| **Plataformas**              | Windows, macOS, Linux (qualquer sistema com Python >= 3.10)                                     |
| **Linhas de codigo-fonte**   | ~5.400 (codigo principal) + ~2.200 (testes)                                                     |

---

## 2. Resumo

O **FastSLR** e um programa de computador que automatiza a etapa de triagem por titulo e resumo em Revisoes Sistematicas da Literatura (RSL). Dado um corpus de artigos exportado de bases bibliograficas (CSV ou XLSX) e um arquivo de configuracao descrevendo o protocolo da revisao, o sistema classifica deterministicamente cada artigo como **APROVADO**, **SINALIZADO** (para revisao manual) ou **REJEITADO**.

O programa opera por correspondencia de padroes baseada em regras, sem qualquer componente de Inteligencia Artificial ou Aprendizado de Maquina. Esta decisao de projeto e deliberada e confere ao sistema tres propriedades criticas para a pesquisa academica: **transparencia** (toda decisao e rastreavel ate termos especificos), **determinismo** (mesma entrada + mesma configuracao = mesma saida, sempre) e **reprodutibilidade total** (hashes criptograficos garantem auditoria completa).

---

## 3. Contexto e Motivacao

### 3.1 Problema

A triagem manual em Revisoes Sistematicas da Literatura e um processo lento, subjetivo e irreproducivel. Uma RSL tipica envolve centenas a milhares de artigos candidatos que devem ser avaliados contra criterios de inclusao e exclusao. Quando realizada manualmente, esta etapa sofre de:

- **Discordancia inter-revisores:** dois revisores aplicando os mesmos criterios ao mesmo corpus frequentemente produzem resultados divergentes.
- **Erros por fadiga:** a monotonia da tarefa repetitiva causa omissoes e classificacoes inconsistentes.
- **Irreproducibilidade:** nao ha garantia de que o processo produzira resultados identicos se repetido.
- **Tempo excessivo:** revisoes com milhares de artigos podem demandar semanas de triagem manual.

### 3.2 Solucao Proposta

O FastSLR resolve estes problemas oferecendo um motor de triagem que:

1. **Automatiza** a classificacao baseada em termos de busca definidos pelo pesquisador.
2. **Garante determinismo** -- execucoes repetidas com os mesmos dados e configuracao produzem resultados identicos bit a bit.
3. **Documenta cada decisao** com termos encontrados, pontuacoes computadas e razoes explicitas.
4. **Gera trilha de auditoria** completa com hashes SHA-256 para verificacao de integridade.
5. **Suporta diferentes protocolos** atraves de configuracao flexivel de blocos tematicos, niveis de relevancia e politicas de decisao.

### 3.3 Publico-alvo

Pesquisadores de qualquer area do conhecimento que conduzem revisoes sistematicas ou de escopo e necessitam de triagem transparente, reprodutivel e documentavel para a secao de metodos de suas publicacoes. O programa foi projetado para ser acessivel a pesquisadores sem formacao em programacao, oferecendo tanto uma interface de linha de comando (CLI) quanto uma interface textual interativa (TUI).

---

## 4. Objetivos do Programa

### 4.1 Objetivo Geral

Fornecer uma ferramenta deterministica de triagem automatizada para Revisoes Sistematicas da Literatura que substitua a classificacao manual por titulo e resumo, produzindo resultados transparentes, reprodutiveis e auditaveis.

### 4.2 Objetivos Especificos

1. Classificar artigos em APROVADO, SINALIZADO ou REJEITADO com base em termos de busca configurados pelo pesquisador.
2. Suportar multiplos blocos tematicos (dominios) com avaliacao independente e composicao configuravel.
3. Oferecer cinco niveis de relevancia com pontuacao ponderada por secao do artigo (titulo, resumo, palavras-chave).
4. Implementar sistema de anti-termos para exclusao e sinalizacao automaticas.
5. Gerar protocolo de execucao com hashes criptograficos para reprodutibilidade total.
6. Disponibilizar interfaces CLI e TUI adequadas a pesquisadores com diferentes niveis de proficiencia tecnica.
7. Suportar internacionalizacao (Ingles, Portugues BR, Espanhol).
8. Produzir pacote academico (ZIP) pronto para submissao como material suplementar.

---

## 5. Fundamentacao Tecnica

### 5.1 Filosofia de Projeto: Ausencia Deliberada de IA/ML

O FastSLR faz uma **escolha consciente e deliberada** de nao utilizar componentes de Inteligencia Artificial ou Aprendizado de Maquina. Esta nao e uma limitacao, mas um trade-off que prioriza tres propriedades essenciais:

| Propriedade        | Descricao                                                                                          |
|--------------------|-----------------------------------------------------------------------------------------------------|
| **Transparencia**  | Toda decisao e rastreavel a correspondencias especificas de termos, pontuacoes e comparacoes de limiares. Nao ha pesos opacos de modelo nem inferencia estocastica. |
| **Determinismo**   | Dados de entrada identicos e configuracao identica produzem saida identica bit a bit, em qualquer plataforma, sem excecao. |
| **Reprodutibilidade** | Qualquer pesquisador pode reproduzir os resultados exatos utilizando os mesmos arquivos de configuracao e dados de entrada. O snapshot de protocolo captura tudo o que e necessario. |

### 5.2 Validacao em RSL Real

O FastSLR foi validado em uma RSL real sobre *Inteligencia Artificial na Gestao da Cadeia de Suprimentos de Petroleo e Gas* (Protocolo v12, Janeiro 2026):

| Metrica                        | Valor                                              |
|--------------------------------|----------------------------------------------------|
| Artigos processados            | 505 unicos (de 2.519 hits brutos em 4 bases)       |
| Tempo de processamento         | 6,91 segundos                                      |
| Taxa de processamento          | 73,0 artigos/segundo                               |
| Corpus final                   | 38 artigos (taxa de inclusao de 7,5%)              |
| APROVADOS                      | 43 (8,5%)                                          |
| SINALIZADOS                    | 147 (29,1%)                                        |
| REJEITADOS                     | 315 (62,4%)                                        |
| Economia por fail-fast         | ~49% das avaliacoes de bloco foram dispensadas      |
| Blocos de dominio              | 3 (T1A: Petroleo e Gas, T1B: IA, T1C: SCM)        |

---

## 6. Arquitetura do Sistema

### 6.1 Visao Geral em Camadas

O FastSLR segue uma arquitetura em camadas com separacao estrita de responsabilidades:

```
+-----------------------------------------------+
|        Camada de Interface do Usuario         |
|  +------------------+  +-------------------+  |
|  |   CLI            |  |   TUI             |  |
|  |  (typer + rich)  |  |  (textual)        |  |
|  +--------+---------+  +--------+----------+  |
+-----------|----------------------|-------------+
            |                      |
+-----------v----------------------v-------------+
|        Camada de Aplicacao                     |
|  +------------------------------------------+ |
|  |  controller.py (orquestracao unica)       | |
|  |  profiles.py (gerenciamento de perfis)    | |
|  +------------------------------------------+ |
+----------------------|-------------------------+
                       |
+-----------v----------v-------------------------+
|        Camada do Motor Central (Core)          |
|  +-----------+  +------------+  +----------+   |
|  | config.py |  | scoring.py |  | engine.py|   |
|  +-----------+  +------------+  +----------+   |
|  +-----------+  +------------+  +----------+   |
|  |patterns.py|  |coverage.py |  |adapters  |   |
|  +-----------+  +------------+  +----------+   |
|  +-----------+  +------------+  +----------+   |
|  |  models   |  | constants  |  | presets  |   |
|  +-----------+  +------------+  +----------+   |
|  +------------------------------------------+  |
|  | normalization.py (motor de normalizacao)  |  |
|  +------------------------------------------+  |
+-----------------------|------------------------+
                        |
+-----------------------v------------------------+
|        Camada de Entrada/Saida                 |
|  +------------------------------------------+ |
|  |  io.py (CSV/XLSX, exportacao, relatorios) | |
|  +------------------------------------------+ |
+-----------------------|------------------------+
                        |
+-----------------------v------------------------+
|        Internacionalizacao (i18n)              |
|  +------------------------------------------+ |
|  |  __init__.py + locales (en, pt_BR, es)   | |
|  +------------------------------------------+ |
+------------------------------------------------+
```

**Principio de projeto:** Nem a CLI nem a TUI importam diretamente do `core/`. Toda orquestracao passa pelo `controller.py`, que e o ponto unico de contato entre a camada de aplicacao e o motor central. Isto garante que ambas as interfaces compartilhem logica identica e que o motor permanca agnositco a interface.

### 6.2 Mapa de Modulos

| Modulo           | Arquivo               | Linhas | Responsabilidade                                                    |
|------------------|-----------------------|-------:|---------------------------------------------------------------------|
| `scoring`        | `core/scoring.py`     |    548 | Correspondencia de termos, avaliacao de blocos, pre-triagem T0, arvore de decisao final |
| `engine`         | `core/engine.py`      |    324 | Pipeline de processamento de artigos, coleta de estatisticas, auto-mapeamento de colunas |
| `io`             | `core/io.py`          |    746 | E/S CSV/XLSX, exportacao, highlighting, relatorios, snapshots de protocolo, pacote academico |
| `controller`     | `app/controller.py`   |    679 | Orquestracao: triagem, preview, cobertura, diff, criacao de projeto, exportacao |
| `tui`            | `app/tui.py`          |    870 | 10 telas interativas via Textual                                    |
| `scoring`        | `core/scoring.py`     |    548 | Correspondencia de termos, avaliacao de blocos, pre-triagem T0      |
| `cli`            | `app/cli.py`          |    439 | 10 comandos CLI via Typer com saida Rich                            |
| `config`         | `core/config.py`      |    333 | Carga de configuracao, validacao JSON Schema, parsing de termos CSV |
| `patterns`       | `core/patterns.py`    |    245 | Compilacao de padroes (exato, wildcard, proximidade), deteccao de termos compostos |
| `coverage`       | `core/coverage.py`    |    243 | Analise de cobertura: termos inativos, termos abrangentes, discriminacao entre blocos |
| `models`         | `core/models.py`      |    194 | Classes de dados: `GlobalParams`, `BlockEvaluation`, `T0Evaluation`, `TermMatch`, `AntiHit` |
| `adapters`       | `core/adapters.py`    |    184 | Deteccao de formato bibliografico (Zotero, Scopus, Web of Science)  |
| `presets`        | `core/presets.py`     |    160 | Presets de niveis (binario/simples/padrao), geracao de configuracao  |
| `normalization`  | `core/normalization.py`|   128 | Motor de normalizacao de texto com cache LRU                        |
| `i18n`           | `i18n/__init__.py`    |    130 | Deteccao de locale, traducao baseada em JSON, cadeia de fallback    |
| `profiles`       | `app/profiles.py`     |    110 | Salvar/carregar/listar perfis de configuracao                       |
| `constants`      | `core/constants.py`   |     64 | Versao, defaults, valores validos, nomes de secao                   |
| **Total**        |                       | **5.397** |                                                                  |

### 6.3 Pilha Tecnologica

| Dependencia    | Versao     | Funcao                                                                      |
|----------------|------------|-----------------------------------------------------------------------------|
| **Python**     | >= 3.10    | Runtime. Requer `match` statements, tipos uniao `X | Y`, `ParamSpec`.       |
| **pandas**     | >= 2.0     | Manipulacao de dados tabulares. Operacoes em DataFrame, I/O CSV/XLSX.       |
| **openpyxl**   | >= 3.1     | Exportacao XLSX. Requerido pelo pandas para escrita `.xlsx`.                 |
| **typer**      | >= 0.12    | Framework CLI. Comandos com anotacao de tipos, `--help` automatico.         |
| **rich**       | >= 13.0    | Formatacao terminal. Barras de progresso, tabelas estilizadas, cores.       |
| **textual**    | >= 0.80    | Framework TUI. Interface terminal com CSS, DataTables, Input, RadioSets.    |
| **jsonschema** | >= 4.20    | Validacao de configuracao contra JSON Schema no momento do carregamento.     |
| **chardet**    | >= 5.0 *(opc.)* | Deteccao automatica de encoding de arquivos CSV. Fallback: UTF-8.      |

**Dependencias de desenvolvimento** (nao requeridas em runtime): `pytest`, `pytest-cov`, `ruff`, `pyright`, `coverage`.

---

## 7. Descricao do Algoritmo

### 7.1 Pipeline de Processamento

O pipeline de processamento segue uma sequencia deterministica para cada artigo:

```
ENTRADA (CSV/XLSX)
    |
    v
[1. Carga e Deteccao de Formato]
  - Deteccao de encoding (chardet, opcional)
  - Deteccao de separador (;  ,  tab)
  - Deteccao de formato bibliografico (Zotero/Scopus/WOS)
  - Auto-mapeamento de colunas (exato -> case-insensitive -> aliases)
    |
    v
[2. Carga de Configuracao e Termos]
  - Validacao contra JSON Schema
  - Parsing de termos CSV
  - Pre-compilacao de padroes regex
    |
    v
[3. Loop de Processamento] <-- PARA CADA ARTIGO
    |
    v
[3.1 Normalizacao de Texto]
  - Expansao de abreviaturas (AI -> artificial intelligence)
  - Substituicao de simbolos (& -> and)
  - Unificacao de compostos (supply-chain -> supply chain)
  - Colapso de espacos em branco
  - Cache LRU (2.000 entradas)
    |
    v
[3.2 Pre-Triagem T0] (se configurada)
  - Anti-exclusao global -> REJEITADO (curto-circuito)
  - Anti-sinalizacao global -> SINALIZADO (continua para blocos)
    |
    v
[3.3 Avaliacao de Blocos de Dominio] <-- PARA CADA BLOCO
  - Encontrar termos positivos em cada secao
  - Computar pontuacao bruta por secao
  - Aplicar pesos de secao (titulo 2.0x, resumo 1.0x, tags 1.5x)
  - Aplicar uplift sem-tags (1.17x se tags ausentes)
  - Limitar pontuacao por secao (cap = 30)
  - Verificar anti-termos (exclusao e sinalizacao)
  - Comparar com limiares de aprovacao/sinalizacao
  - Se REJEITADO e fail-fast ativo -> pular blocos restantes
    |
    v
[3.4 Decisao Final]
  - Combinar status de todos os blocos conforme politica:
    * special: regra padrao + override por pontuacao alta
    * strict: todos os blocos devem aprovar
    * k_of_n: pelo menos K blocos devem aprovar
    |
    v
SAIDA (XLSX/CSV + Protocolo JSON + Relatorios + Pacote Academico ZIP)
```

### 7.2 Motor de Correspondencia de Termos

O sistema suporta tres tipos de correspondencia:

**Correspondencia Exata:** termos literais sao compilados com word boundaries (`\b`) para evitar correspondencias parciais. Metacaracteres regex sao escapados. Case-insensitive.

- Exemplo: `"machine learning"` compila para `\b(machine learning)\b`

**Correspondencia Wildcard:** o caractere `*` expande para `\w*` (zero ou mais caracteres de palavra), permitindo truncacao no estilo de bases bibliograficas.

- Exemplo: `"industr*"` compila para `\bindustr\w*\b`, correspondendo a "industry", "industries", "industrial" etc.

**Deteccao de Proximidade:** termos compostos conectados por `and`, `&`, `or` ou `/` geram padroes bidirecionais com tolerancia a gap configuravel.

- Exemplo: `"supply and demand"` com MAX_GAP=2 encontra "supply ... demand" com ate 2 tokens intermediarios, em qualquer ordem.

### 7.3 Sistema de Pontuacao

A pontuacao e computada por **niveis unicos encontrados por secao**, nao por contagem de correspondencias individuais. Se 5 termos diferentes correspondem no nivel 3, a pontuacao do nivel 3 (6 pontos) e contada apenas uma vez. Isto previne que a inflacao da lista de termos distorca as pontuacoes.

**Tabela de pontuacao padrao (preset standard):**

| Nivel | Pontos | Significado semantico                              |
|-------|--------|-----------------------------------------------------|
| 1     | 10     | Essencial / correspondencia exata a questao de pesquisa |
| 2     | 8      | Diretamente relacionado                             |
| 3     | 6      | Foco da pesquisa                                    |
| 4     | 4      | Processos / metodos                                 |
| 5     | 2      | Contexto amplo                                      |

**Pesos de secao padrao:**

| Secao          | Peso  | Justificativa                                       |
|----------------|-------|-----------------------------------------------------|
| `title`        | 2.0x  | Termos no titulo sao o sinal de relevancia mais forte |
| `abstract`     | 1.0x  | Peso de referencia                                  |
| `manual_tags`  | 1.5x  | Palavras-chave atribuidas pelo autor sao sinais fortes |

**Formula:**
```
pontuacao_bruta = (score_titulo * 2.0) + (score_resumo * 1.0) + (score_tags * 1.5)

Se tags ausentes E pontuacao_bruta > 0:
    pontuacao_final = pontuacao_bruta * 1.17  (compensacao por dados ausentes)
Senao:
    pontuacao_final = pontuacao_bruta
```

### 7.4 Sistema de Anti-termos

Anti-termos disparam acoes negativas quando encontrados:

| Tipo                | Acao                                                              |
|---------------------|-------------------------------------------------------------------|
| **Anti-exclusao**   | Rejeicao imediata do artigo naquele bloco. Nao ha avaliacao adicional. |
| **Anti-sinalizacao**| Rebaixa o artigo para SINALIZADO para revisao manual.             |

Anti-termos globais (bloco `GLOBAL`/`T0`) operam antes da avaliacao por bloco, permitindo exclusao rapida de artigos claramente fora do escopo.

### 7.5 Politicas de Decisao Final

| Politica  | Logica                                                                                  |
|-----------|-----------------------------------------------------------------------------------------|
| `special` | Regra padrao: qualquer bloco rejeitado -> rejeitado. Regra especial: se exatamente 1 bloco sinalizado e demais com score >= 40 -> aprovado. |
| `strict`  | Todos os blocos devem aprovar. Qualquer sinalizacao impede aprovacao.                   |
| `k_of_n`  | Pelo menos K blocos devem aprovar (K configuravel). Permite flexibilidade controlada.   |

### 7.6 Avaliacao Fail-Fast

Quando um bloco rejeita um artigo, os blocos restantes sao marcados como `NAO_AVALIADO` e o artigo e imediatamente rejeitado. Esta otimizacao e metodologicamente segura pois todos os blocos sao obrigatorios -- se um artigo falha em qualquer bloco, nao pode passar na triagem geral.

**Impacto medido:** ~49% de economia de processamento na RSL real (505 artigos, 3 blocos).

---

## 8. Sistema de Configuracao

### 8.1 Estrutura do Arquivo de Configuracao

O arquivo `config.json` possui quatro secoes principais:

```json
{
  "global": {
    "DECISION_POLICY": "special",
    "FAIL_FAST_GLOBAL": true,
    "PONTUACAO_NIVEIS": {"1": 10, "2": 8, "3": 6, "4": 4, "5": 2},
    "LIMITES_APROVADO": {"1": 10, "2": 12, "3": 18, "4": 22, "5": null},
    "LIMITES_SINALIZADO": {"1": 6, "2": 6, "3": 6, "4": 7, "5": 12},
    "WEIGHTS": {"title": 2.0, "abstract": 1.0, "manual_tags": 1.5},
    "..."
  },
  "fields": {
    "id": "key", "title": "title", "abstract": "abstract", "manual_tags": "manual_tags"
  },
  "output": {
    "xlsx": true, "academic_package": true
  },
  "encoding": "utf-8-sig",
  "sep": ";"
}
```

A configuracao e validada contra um JSON Schema embutido no momento do carregamento, garantindo que parametros invalidos sejam detectados antes do processamento.

### 8.2 Presets de Niveis

| Preset     | Niveis | Caso de uso                                 |
|------------|--------|---------------------------------------------|
| `binary`   | 1      | Triagem rapida incluir/excluir              |
| `simple`   | 3      | Granularidade moderada                      |
| `standard` | 5      | Granularidade completa (recomendado)        |

### 8.3 Definicao de Termos

Termos podem ser definidos em formato CSV (recomendado para conjuntos grandes) com as colunas:

| Coluna          | Obrigatoria | Descricao                                                 |
|-----------------|-------------|-----------------------------------------------------------|
| `block`         | Sim         | Nome do bloco (ex.: CTX, TECH). `GLOBAL` para anti-termos globais |
| `kind`          | Sim         | Tipo: `pos` (positivo), `anti` (exclusao), `flag` (sinalizacao)  |
| `term`          | Sim         | Texto do termo de busca                                    |
| `level`         | Nao         | Nivel de relevancia (1-5). Obrigatorio para termos `pos`   |
| `section_scope` | Nao         | Escopo: `title`, `abstract`, `manual_tags` ou `any`        |
| `is_regex`      | Nao         | `1` para regex, `0` para literal                           |

---

## 9. Dados de Entrada e Saida

### 9.1 Entrada

**Formatos aceitos:** CSV e XLSX

**Colunas minimas requeridas:**
- Identificador do artigo (ID)
- Titulo do artigo
- Resumo do artigo

**Coluna opcional:** Palavras-chave/tags manuais (melhora a precisao da pontuacao)

**Deteccao automatica de formatos bibliograficos:**

| Formato         | Colunas de assinatura                          | Mapeamento automatico                   |
|-----------------|------------------------------------------------|-----------------------------------------|
| Zotero          | `Key`, `Item Type`, `Abstract Note`            | id=Key, titulo=Title, resumo=Abstract Note, tags=Manual Tags |
| Scopus          | `EID`, `Source title`, `Cited by`              | id=EID, titulo=Title, resumo=Abstract, tags=Author Keywords  |
| Web of Science  | `UT`, `TI`, `AB`, `SO`                        | id=UT, titulo=TI, resumo=AB, tags=DE                        |

### 9.2 Saida

Cada execucao de triagem produz os seguintes artefatos:

| Artefato                  | Formato  | Conteudo                                                                  |
|---------------------------|----------|---------------------------------------------------------------------------|
| `triage_results.xlsx`     | XLSX     | Uma linha por artigo: ID, pontuacoes por bloco, status, decisao final, razao, termos encontrados |
| `triage_report.txt`       | Texto    | Resumo legivel: versao, data, total de artigos, tempo, distribuicao de decisoes |
| `protocol.json`           | JSON     | Snapshot de protocolo v2.1 com hashes SHA-256 para reprodutibilidade      |
| `academic_report.md`      | Markdown | Relatorio de conformidade academica: configuracao, criterios, metricas    |
| `config_audit.json`       | JSON     | Configuracao sanitizada com metadados de auditoria                        |
| `academic_package.zip`    | ZIP      | Todos os artefatos acima empacotados para material suplementar            |

### 9.3 Estrutura da Planilha de Resultados

Para cada artigo, a planilha de saida contem:

**Colunas por bloco de dominio** (ex.: CTX, TECH, METHOD):
- `RawScore_{bloco}` -- Soma bruta das pontuacoes de correspondencia
- `FinalScore_{bloco}` -- Pontuacao ponderada apos pesos de secao e uplift
- `BestLevel_{bloco}` -- Nivel de relevancia mais alto (menor numero) encontrado
- `Status_{bloco}` -- Veredito: APPROVED, FLAGGED, REJECTED ou NOT_EVALUATED
- `Highlights_{bloco}` -- Termos positivos encontrados com secao e nivel
- `AntiHighlights_{bloco}` -- Anti-termos encontrados
- `Flags_{bloco}` -- Alertas e metadados

**Colunas finais:**
- `Final_Decision` -- APPROVED_FINAL, FLAGGED_FINAL ou REJECTED_FINAL
- `Final_Reason` -- Explicacao legivel da decisao

### 9.4 Protocolo de Reprodutibilidade

O snapshot de protocolo (v2.1) captura todas as informacoes necessarias para reproduzir uma execucao:

- Hash SHA-256 do arquivo de entrada
- Hash SHA-256 da configuracao utilizada
- Politica de decisao e definicoes de blocos
- Pontuacoes, pesos e limiares
- Metricas de processamento (total, tempo, taxa)
- Flag de determinismo: `true`

**Garantia:** se duas execucoes compartilham o mesmo `config_hash` e `input_hash`, elas sao garantidas de produzir resultados identicos.

---

## 10. Interfaces do Usuario

### 10.1 Interface de Linha de Comando (CLI)

O FastSLR oferece 10 comandos via CLI:

| Comando              | Funcao                                                        |
|----------------------|---------------------------------------------------------------|
| `fastslr run`        | Executar triagem completa no corpus de artigos                |
| `fastslr preview`    | Visualizar resultados em amostra sem gerar arquivos           |
| `fastslr coverage`   | Analisar cobertura de termos no corpus                        |
| `fastslr diff`       | Comparar dois arquivos de resultado                           |
| `fastslr new-project`| Criar novo projeto com templates de configuracao              |
| `fastslr export`     | Gerar pacote academico (ZIP) a partir dos resultados          |
| `fastslr terms`      | Navegar e inspecionar termos configurados                     |
| `fastslr profile`    | Gerenciar perfis de configuracao reutilizaveis                |
| `fastslr tui`        | Abrir interface textual interativa                            |
| `fastslr version`    | Exibir versao instalada                                       |

Todos os comandos suportam o flag `--lang` para selecao de idioma da interface.

### 10.2 Interface Textual Interativa (TUI)

A TUI fornece uma interface dirigida por menus com 10 telas:

| Tecla | Tela                    | Funcao                                                       |
|-------|-------------------------|--------------------------------------------------------------|
| `1`   | Novo Projeto            | Assistente guiado de criacao de projeto com selecao de preset |
| `2`   | Carregar Perfil         | Navegar e carregar perfis de configuracao salvos              |
| `3`   | Editar Configuracao     | Editor JSON integrado para config.json                       |
| `4`   | Navegar Termos          | Tabela filtravel de todos os termos (bloco, tipo, escopo)    |
| `5`   | Executar Triagem        | Triagem com barra de progresso e estatisticas ao vivo        |
| `6`   | Explorar Resultados     | Navegar resultados com filtro por decisao                    |
| `7`   | Analise de Cobertura    | Verificar quais termos corresponderam e quais nao            |
| `8`   | Comparar Execucoes      | Diff entre dois arquivos de resultados                       |
| `9`   | Exportar Pacote         | Gerar arquivo ZIP para publicacao                            |
| `0`   | Configuracoes e Idioma  | Alterar idioma da interface                                  |

A TUI foi projetada para pesquisadores nao-programadores, com linguagem acessivel, ajuda contextual e navegacao visivel.

### 10.3 Internacionalizacao (i18n)

| Idioma              | Codigo  | Exemplo de uso                |
|---------------------|---------|-------------------------------|
| Ingles              | `en`    | Padrao                        |
| Portugues (Brasil)  | `pt_BR` | `fastslr run ... --lang pt_BR`|
| Espanhol            | `es`    | `fastslr run ... --lang es`   |

Prioridade de deteccao: flag `--lang` > variavel `FASTSLR_LANG` > locale do sistema > Ingles.

**Nota:** dados de saida (planilhas, protocolos) permanecem em Ingles para garantir reprodutibilidade entre locales.

---

## 11. Garantia de Qualidade

### 11.1 Suite de Testes

| Modulo de teste                | Linhas | Cobertura                                                     |
|--------------------------------|-------:|---------------------------------------------------------------|
| `test_scoring.py`              |    681 | Algoritmos de pontuacao, correspondencia de termos, limiares  |
| `test_engine.py`               |    247 | Processamento de artigos, estatisticas, auto-mapeamento       |
| `test_compliance.py`           |    228 | Conformidade de protocolo, reprodutibilidade, determinismo    |
| `test_io.py`                   |    215 | E/S CSV/XLSX, formatos de exportacao, snapshots               |
| `test_integration.py`          |    213 | Workflows fim-a-fim, cenarios do mundo real                   |
| `test_config.py`               |    174 | Carga de configuracao, validacao de schema, parsing CSV       |
| `test_coverage_analysis.py`    |    144 | Geracao de relatorio de cobertura                             |
| `test_patterns.py`             |    134 | Compilacao de padroes (exato, proximidade, wildcards)         |
| `test_normalization.py`        |    101 | Motor de normalizacao, cache LRU                              |
| `test_presets.py`              |     96 | Geracao de presets, validacao                                 |
| **Total**                      | **2.233** |                                                            |

### 11.2 Verificacao Estatica

- **Pyright** em modo `standard`: verificacao de tipos em todo o codigo-fonte
- **Ruff**: linting (regras E, F, W, I, UP) e formatacao automatica
- **Limite de linha**: 100 caracteres

### 11.3 Teste de Stress

Documentado em `docs/stress-test-log.md`. O sistema processou 505 artigos reais em 6,91 segundos com validacao completa do protocolo de reproducibilidade, confirmando desempenho e corretude.

---

## 12. Distribuicao e Instalacao

### 12.1 Instalacao

```bash
pip install fastslr
```

Para deteccao automatica de encoding:
```bash
pip install fastslr[chardet]
```

### 12.2 Requisitos Minimos

| Requisito          | Especificacao                    |
|--------------------|----------------------------------|
| Sistema operacional| Windows, macOS ou Linux          |
| Python             | >= 3.10                          |
| Memoria RAM        | 512 MB (minimo)                  |
| Disco              | ~50 MB (com dependencias)        |
| Terminal            | Qualquer terminal com suporte a Unicode (para TUI) |

### 12.3 Codigo-fonte

```bash
git clone https://github.com/Lharden/fastslr.git
cd fastslr
pip install -e ".[dev]"
```

---

## 13. Decisoes de Projeto

As 12 decisoes arquiteturais mais significativas do v3.0.0 estao documentadas formalmente no projeto:

| # | Decisao                                    | Justificativa                                                                      |
|---|---------------------------------------------|------------------------------------------------------------------------------------|
| 1 | Remover todos os componentes de IA/ML       | Sistema 100% mecanico para publicacao academica. Determinismo nao-negociavel.      |
| 2 | Modelo de interacao dual (CLI + TUI)        | Pesquisadores tem preferencias distintas. CLI para scripting; TUI para guiamento.  |
| 3 | Arquitetura hibrida (motor v2.0 + shell novo)| Motor testado e correto. Risco isolado na camada de aplicacao.                    |
| 4 | Interface em ingles com i18n                | Audiencia internacional. Dados de saida em ingles para reproducibilidade.          |
| 5 | 10 telas TUI completas                     | Ferramenta completa para publicacao. Cada tela atende um workflow de pesquisa.     |
| 6 | Distribuicao cross-platform via pip         | `pip install fastslr` e o metodo mais acessivel para academia.                     |
| 7 | Dependencias pragmaticas                   | pandas, typer, textual: bibliotecas estabelecidas com suporte cross-platform.      |
| 8 | Licenca MIT                                | Mais permissiva, padrao em ferramentas academicas, minimiza barreiras de adocao.   |
| 9 | UX projetada para nao-programadores        | Publico-alvo: pesquisadores de areas diversas, maioria sem formacao em programacao.|
| 10| Versao 3.0.0                               | Breaking changes justificam bump de versao major (semver).                         |
| 11| Pyright + ruff + testes de stress          | Publicacao academica exige robustez demonstravel.                                  |
| 12| Remocao do diretorio legacy/               | Supersedido pelo motor universal v2.0-para-v3.0. Historico git preserva o codigo.  |

---

## 14. Licenca

FastSLR e distribuido sob a **Licenca MIT** (codigo aberto).

```
MIT License

Copyright (c) 2026 Leonardo Harden

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 15. Referencia Bibliografica

> Harden, L. (2026). *FastSLR: Motor deterministico de triagem para revisoes sistematicas da literatura* (Versao 3.0.0) [Programa de computador]. https://github.com/Lharden/fastslr

```bibtex
@software{harden2026fastslr,
  author  = {Harden, Leonardo},
  title   = {FastSLR: A Deterministic Triage Engine for Systematic Literature Reviews},
  year    = {2026},
  version = {3.0.0},
  url     = {https://github.com/Lharden/fastslr}
}
```

---

## 16. Documentacao Complementar

| Documento                               | Localizacao                         | Descricao                                              |
|------------------------------------------|-------------------------------------|--------------------------------------------------------|
| README (guia do usuario)                 | `README.md`                         | Instalacao, uso, referencia de comandos                |
| Relatorio Tecnico (ingles)               | `docs/TECHNICAL_REPORT.md`          | Especificacao tecnica completa com diagramas Mermaid   |
| Documento de Design v3                   | `docs/plans/fastslr-v3-design.md`   | Arquitetura e decisoes de projeto                      |
| Log de Decisoes                          | `docs/plans/fastslr-v3-decision-log.md` | 12 decisoes arquiteturais documentadas             |
| Protocolo RSL Completo (v12)             | `docs/rsl/PROTOCOLO_RSL_Completo_v12.md` | Protocolo da RSL em portugues (41 KB)             |
| Log de Testes de Stress                  | `docs/stress-test-log.md`           | Resultados de desempenho e testes de carga            |

---

*Documento gerado em marco de 2026. Versao do programa: FastSLR 3.0.0.*
