---
tags: [fastslr, arquitetura, core]
---

# ⚙️ Arquitetura - Camada Core

O pacote `core/` é o **motor de triagem**: uma biblioteca pura, sem dependência da interface. Pode ser usado programaticamente.

## Módulos

### `engine.py` — orquestração do pipeline
Função central: `process_articles(df, config, on_progress)`. Itera artigo por artigo, executa [[Algoritmo - Pré-triagem T0|T0]] → blocos → [[Algoritmo - Decisão Final|decisão final]], monta o DataFrame de saída e coleta estatísticas (`collect_statistics`). Faz **auto-mapeamento de colunas** (`_auto_map_column`) tolerante a acentos e aliases de Zotero/Scopus/WoS. Trata erros por artigo conforme `ERROR_POLICY` (`flag` mantém o artigo como `FLAGGED_FINAL`; `fail` aborta). Aborta a run inteira se a taxa de erro exceder `MAX_ERROR_RATE`.

### `scoring.py` — coração do algoritmo
Contém o *matching* de termos (`find_positive_terms`, `find_anti_terms`), a [[Algoritmo - Pontuação (Scoring)|pontuação por seção]] (`_compute_section_scores`), a [[Algoritmo - Avaliação de Bloco|avaliação de bloco]] (`evaluate_block`), a [[Algoritmo - Pré-triagem T0|T0]] (`evaluate_t0_conditional`) e a [[Algoritmo - Decisão Final|decisão final]] (`make_final_decision`). Ver detalhes nas notas de Algoritmo.

### `patterns.py` — compilação de padrões
Transforma termos textuais em `re.Pattern` compilados: wildcards (`*`→`\w*`), regex literal (`is_regex=1`), e **proximidade** para termos compostos ("oil and gas"). `precompile_patterns` pré-compila todos os termos de um bloco. Ver [[Algoritmo - Padrões e Proximidade]].

### `normalization.py` — normalização de texto
`NormalizationEngine` aplica regras de **abreviação** (AI → artificial intelligence), **variante composta** (supply-chain → supply chain) e **substituição de símbolo**, com cache LRU manual. Ver [[Algoritmo - Normalização]].

### `config.py` — configuração e termos
`load_config` (JSON), `parse_terms_csv` (tabela de termos CSV/XLSX, com validação linha-a-linha, deduplicação e detecção de conflito pos/anti), `load_global_params` (traduz chaves PT-BR como `PONTUACAO_NIVEIS` em `GlobalParams`), `get_domain_blocks`. Termos com bloco `GLOBAL` viram o bloco **T0**. Ver [[Configuração - config e termos]].

### `models.py` — estruturas de dados
Dataclasses: `TermMatch`, `AntiHit`, `BlockEvaluation`, `T0Evaluation` e `GlobalParams` (o "contrato" de parâmetros do motor). Ver tabela completa em [[Glossário]].

### `constants.py` — defaults
`VERSION`, `SECTION_NAMES = (title, abstract, manual_tags)`, e os defaults de pontuação/thresholds.

> [!bug] Fonte de verdade duplicada
> Os thresholds de *flagging* aparecem em **três** lugares com valores divergentes (constante=8, preset=7, JSON=7 no nível 4). Ver item #1 em [[Validação - Bugs e Riscos Conhecidos]].

### `io.py` — entrada/saída
Carga robusta de CSV/XLSX (detecção de encoding e separador), hashing SHA-256, *highlighting* (`***termo***`), geração de relatórios, snapshot do `protocol.json` e empacotamento ZIP. Ver [[Fluxo de Dados]] e [[Reprodutibilidade e Pacote Acadêmico]].

### `coverage.py` — análise de cobertura
`analyze_term_coverage` identifica **dead terms** (0 matches), **broad terms** (>80% dos artigos) e blocos sem discriminação. Útil na fase de calibração. Ver [[Algoritmo - Pipeline de Triagem]].

### `adapters.py` — importadores bibliográficos
`detect_format` + `apply_mapping` reconhecem exportações de **Zotero**, **Scopus** e **Web of Science** e renomeiam colunas para o esquema interno.

### `presets.py` — presets e scaffolding
`LEVEL_PRESETS` (binary/simple/standard), `generate_config` (cria config completa para `new-project`).

---

Relacionado: [[Arquitetura - Visão Geral]] · [[Arquitetura - Camada App e Controller]] · [[Algoritmo - Pipeline de Triagem]] · [[Home]]
