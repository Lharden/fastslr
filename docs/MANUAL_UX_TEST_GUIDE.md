# FastSLR — Roteiro Interativo de Testes Manuais (UX)

> **Versao**: 1.0  •  **Tempo estimado**: 90–120 min (completo) ou 30 min (smoke)  •  **Modo**: interativo (voce + Claude)
>
> Este e um **roteiro guiado**: voce executa, eu (Claude) analiso a saida, fazemos ajustes em tempo real. Para o protocolo tecnico completo, ver [`docs/TEST_PROTOCOL.md`](TEST_PROTOCOL.md).

---

## Como usar este guia

1. **Abra um terminal** na raiz do projeto (`fastslr/`).
2. **Cole cada comando** na ordem. Apos rodar, **me cole a saida** ou descreva o que viu.
3. Em cada **CHECKPOINT**, vou pedir sua avaliacao (1–5 estrelas) e propor ajustes.
4. Apos cada **CENARIO**, eu sintetizo achados e proponho proximos passos.
5. Se algo quebrar, copio o stack trace e investigo.

> **Observacao**: estamos em `master @ 7a18258`. Os artefatos modificados foram comitados.

---

## Pre-requisitos (5 min)

```bash
# Verificar instalacao
python --version    # esperado: 3.10+
fastslr version     # esperado: 3.0.0
```

Se `fastslr` nao for um comando, instale em modo dev:

```bash
pip install -e ".[dev]"
```

**CHECKPOINT 0** — Me diga:
- Sua versao do Python: `_____`
- Saida de `fastslr version`: `_____`
- Sistema operacional (Windows nativo? WSL? Mac? Linux?): `_____`
- Tem Excel/LibreOffice instalado? `_____`

---

## Setup de fixtures (10 min)

Vamos criar um corpus de teste com 20 artigos sinteticos. Voce pode usar seu `data/Final_Corpus_Raw.csv` real **OU** o sintetico que vou propor abaixo. Recomendo o sintetico para ter resultados previsiveis.

### Opcao A — Corpus sintetico (recomendado para o roteiro)

Crie `tests/fixtures/manual_ux_corpus.csv`:

```csv
ID,Title,Abstract,Manual Tags
A001,"Optimization of subsea oil and gas production using AI","We propose a deep learning approach to optimize subsea production systems for oil and gas.","subsea; oil; gas; AI; deep learning"
A002,"Treatment of municipal wastewater with activated sludge","An empirical study on activated sludge for municipal water treatment.","wastewater; treatment"
A003,"Reservoir characterization with seismic inversion","Seismic data is inverted to characterize hydrocarbon reservoirs.","seismic; reservoir; oil"
A004,"Machine learning for medical image segmentation","CNN-based segmentation in MRI images.",""
A005,"Drilling automation in deepwater wells","Automation reduces NPT in deepwater drilling.",
A006,"Subsea pipeline integrity monitoring with fiber optics","Distributed acoustic sensing on subsea pipelines.","subsea; pipeline; DAS"
A007,"Offshore wind farm grid integration","Grid integration challenges for offshore wind.","wind; offshore; grid"
A008,"AI-driven well log interpretation","Transformer model for well log facies classification.","---"
A009,"","Empty title test","oil; gas"
A010,"Test article with no abstract","","oil"
A011,"Subsea production system reliability","A reliability framework for subsea trees and manifolds.","reliability; subsea"
A012,"Carbon capture from natural gas processing","CO2 capture from gas streams.","CCS; gas; CO2"
A013,"Petroleum geology of the Santos Basin","Stratigraphy and petroleum systems of the Santos pre-salt.","geology; petroleum; pre-salt"
A014,"Renewable energy storage with hydrogen","Hydrogen as a renewable carrier.","hydrogen; renewable"
A015,"Subsea boosting and processing","Subsea processing technologies for marginal fields.","subsea; boosting"
A016,"Bayesian inference in production forecasting","Bayesian methods to forecast oil production.","bayesian; oil; forecasting"
A017,"Polymer flooding for enhanced oil recovery","Polymer EOR in carbonate reservoirs.","EOR; polymer; oil"
A018,"Cybersecurity in industrial control systems","SCADA cybersecurity for offshore platforms.","SCADA; cyber; offshore"
A019,"N/A","Pure noise: cooking recipes for vegan lasagna.","N/A"
A020,"Digital twin for FPSO operations","A digital twin framework for FPSO real-time monitoring.","digital twin; FPSO"
```

### Opcao B — Corpus real

Aponte para `data/Final_Corpus_Raw.csv` (gitignored, mas deve existir local).

**CHECKPOINT 1** — Qual opcao voce escolheu? Me cole as primeiras 3 linhas do arquivo.

---

## CENARIO 1 — `doctor`: validacao pre-execucao (10 min)

**Objetivo de UX**: o `doctor` deve dar feedback claro **antes** de o usuario perder tempo rodando o pipeline com config quebrada.

### Passo 1.1 — Criar projeto template

```bash
fastslr new-project ux_test -b "OG,SUBSEA,AI"
```

**O que esperar**: cria pasta `ux_test/` com `config.json` e `terms.csv`.

**CHECKPOINT 1.1** —
- Quantos arquivos foram criados em `ux_test/`?
- A mensagem final do comando foi clara? (vamos avaliar 1–5 estrelas no final do cenario)
- O `config.json` tem comentarios/documentacao inline ou e cru?

### Passo 1.2 — Editar `terms.csv`

Abra `ux_test/terms.csv`. Substitua o conteudo pelos termos abaixo (ajuste para o formato esperado pelo template — o template tem o cabecalho correto):

| block | kind | term | level | section_scope | is_regex |
|---|---|---|---|---|---|
| OG | positive | oil | 2 | all | false |
| OG | positive | gas | 2 | all | false |
| OG | positive | petroleum | 1 | all | false |
| OG | positive | reservoir | 2 | all | false |
| OG | anti_exclude | wastewater | - | all | false |
| OG | anti_flag | vegan | - | all | false |
| SUBSEA | positive | subsea | 1 | all | false |
| SUBSEA | positive | offshore | 3 | all | false |
| SUBSEA | positive | FPSO | 1 | all | false |
| SUBSEA | positive | pipeline | 3 | all | false |
| AI | positive | machine learning | 1 | all | false |
| AI | positive | deep learning | 1 | all | false |
| AI | positive | transformer | 2 | all | false |
| AI | positive | bayesian | 3 | all | false |

### Passo 1.3 — Rodar `doctor`

```bash
fastslr doctor --input tests/fixtures/manual_ux_corpus.csv -c ux_test/config.json -t ux_test/terms.csv
```

**O que avaliar**:
- (a) Detectou as colunas do CSV (`Title`, `Abstract`, `Manual Tags`)?
- (b) Validou os 14 termos sem erro?
- (c) Apontou aviso para `A009` (titulo vazio) ou `A010` (abstract vazio)?
- (d) Aviso para `A019` (`Manual Tags = "N/A"`) — viu se o sistema considera tags presentes ou ausentes? **Esse e o achado F-03 do protocolo**.

### Passo 1.4 — Quebrar de proposito

Edite `ux_test/config.json` e troque `"DECISION_POLICY": "k_of_n"` por `"DECISION_POLICY": "magic_unicorn"`. Rode `doctor` de novo.

**CHECKPOINT 1.2** —
- O erro foi imediato e claro?
- A mensagem indica **qual chave** esta errada e **quais valores** sao validos?
- Avaliacao de UX para o `doctor` (1–5): `_____`
- Sugestoes de melhoria: `_____`

> **Reverta**: troque de volta para `"k_of_n"` antes do proximo cenario.

---

## CENARIO 2 — `preview`: amostragem rapida (5 min)

**Objetivo de UX**: o usuario deve poder ver "como o pipeline esta classificando" antes de rodar o corpus inteiro.

### Passo 2.1

```bash
fastslr preview tests/fixtures/manual_ux_corpus.csv -c ux_test/config.json -t ux_test/terms.csv -s 10
```

**O que esperar**: 10 artigos amostrados com decisoes preliminares.

**CHECKPOINT 2** —
- A saida cabe na sua tela ou ha overflow horizontal?
- As cores/highlights ajudam a entender o motivo da decisao?
- Avaliacao (1–5): `_____`
- Sugestoes: `_____`

> **Bug em potencial**: no protocolo tecnico, item **A1**, mencionei que o sampling pode ser nao-deterministico. Rode 2x. As 10 amostras sao as mesmas?

---

## CENARIO 3 — `run`: pipeline completo (15 min)

**Objetivo de UX**: feedback de progresso, qualidade do output, mensagens de erro graciosas.

### Passo 3.1 — Run feliz

```bash
fastslr run tests/fixtures/manual_ux_corpus.csv -c ux_test/config.json -t ux_test/terms.csv -o ux_test/out_v1/
```

**Avaliar**:
- (a) Barra de progresso atualiza em tempo real?
- (b) Tempo total razoavel (esperado <2s para 20 artigos)?
- (c) Quantos arquivos em `ux_test/out_v1/`? Esperado 6+: xlsx, csv, txt, json (config snapshot, protocol, summary), zip.

### Passo 3.2 — Inspecionar resultados

Abra `ux_test/out_v1/results.xlsx` (ou o csv equivalente) e verifique:

| ID | Decisao esperada | Decisao obtida | OK? |
|---|---|---|---|
| A001 | APPROVED (oil + gas + AI + subsea) | ___ | ___ |
| A002 | REJECTED (wastewater anti-exclude) | ___ | ___ |
| A006 | APPROVED (subsea + pipeline) | ___ | ___ |
| A009 | ? (titulo vazio) | ___ | ___ |
| A019 | FLAGGED (vegan anti-flag, mas N/A em tags) | ___ | ___ |

> **Achado vivo**: A019 e o teste de **F-03**. Se `Manual Tags = "N/A"`, o sistema **deveria** aplicar uplift (porque na pratica nao tem tags), mas **nao aplica** (hardcoded so reconhece "nan", "none", "null"). Verifique a coluna `uplift_applied` no XLSX. Se for `False` para A019, **F-03 confirmado em runtime**.

### Passo 3.3 — Erro intencional

Edite `tests/fixtures/manual_ux_corpus.csv` e troque o titulo de A005 por uma string **muito longa** (5000 chars) ou contendo caracteres unicode raros (`𓂀𓅓𓏏`). Rode `fastslr run` de novo, com `-o ux_test/out_v2/`.

**CHECKPOINT 3** —
- O pipeline aguentou? Crashed? Foi flagged como ERR_5?
- Mensagem de erro foi acionavel? (ou so um stack trace?)
- A05 com unicode raro: o highlight no XLSX renderiza? Ou aparece como `?` ou box?
- Avaliacao do `run` (1–5): `_____`
- Sugestoes: `_____`

> **Reverta**: restaure o A005 original.

---

## CENARIO 4 — `coverage`: descoberta de termos mortos/amplos (10 min)

**Objetivo de UX**: a analise de cobertura deve responder "quais termos do meu glossario nao estao puxando nada?" e "quais sao genericos demais?"

### Passo 4.1

```bash
fastslr coverage tests/fixtures/manual_ux_corpus.csv -c ux_test/config.json -t ux_test/terms.csv
```

**Avaliar**:
- (a) Tabela mostra hit count por termo?
- (b) Termos mortos (zero hits) destacados?
- (c) Termos amplos (>80% hits) destacados?
- (d) **Bug F-12**: termos que voce **sabe** que aparecem em pelo menos 1 artigo (ex.: `oil`) tem `count > 0`?

### Passo 4.2 — Termo deliberadamente morto

Adicione ao `terms.csv`: `OG, positive, brontosaurus, 5, all, false`. Rode `coverage` de novo.

**CHECKPOINT 4** —
- `brontosaurus` aparece com 0 hits? Ou nao aparece?
- O comando sugere **acao** (remover termo, tornar mais amplo, etc.)?
- Avaliacao (1–5): `_____`

---

## CENARIO 5 — `diff`: comparar dois runs (10 min)

**Objetivo de UX**: o usuario refina config/termos e quer ver "o que mudou na minha triagem entre v1 e v2?"

### Passo 5.1

Edite `ux_test/config.json` e mude `"NO_TAGS_UPLIFT": 1.17` para `1.5`. Rode:

```bash
fastslr run tests/fixtures/manual_ux_corpus.csv -c ux_test/config.json -t ux_test/terms.csv -o ux_test/out_v3/
fastslr diff ux_test/out_v1/results.xlsx ux_test/out_v3/results.xlsx
```

**Avaliar**:
- Ha transicoes (`REJECTED → APPROVED` ou vice-versa) reportadas?
- A diff e legivel? (artigos listados? razoes?)

**CHECKPOINT 5** —
- Avaliacao (1–5): `_____`
- O diff te ajudaria a decidir se vale ou nao mudar o uplift? `_____`

---

## CENARIO 6 — `tui`: interface interativa (15 min)

**Objetivo de UX**: a TUI e atalho ou complica?

### Passo 6.1

```bash
fastslr tui
```

Voce vai entrar na TUI (Textual). Navegue pelas 10 telas:
1. New Project
2. Load Profile
3. Edit Config
4. Browse Terms
5. Run Triage
6. Results Explorer
7. Coverage
8. Compare
9. Export
10. Settings

**Tente**:
- (a) Carregar `ux_test/config.json` em "Edit Config".
- (b) Visualizar termos em "Browse Terms".
- (c) Rodar uma triagem em "Run Triage" sobre o corpus de teste.
- (d) Comparar `out_v1/` vs `out_v3/` em "Compare".
- (e) Mudar idioma em "Settings" para `pt_BR` ou `es`.

**CHECKPOINT 6** — Para cada tela, me diga:
- A navegacao por teclado funciona? (Tab, setas, Enter, Esc)
- Atalhos visiveis ou ocultos?
- Mensagens de erro renderizam direito ou cortam?
- A TUI e mais ou menos eficiente que a CLI para voce?
- Avaliacao geral (1–5): `_____`

---

## CENARIO 7 — i18n (5 min)

**Objetivo de UX**: traducoes pt_BR/es sao corretas e completas?

### Passo 7.1

```bash
fastslr run tests/fixtures/manual_ux_corpus.csv -c ux_test/config.json -t ux_test/terms.csv -o ux_test/out_pt/ -l pt_BR
fastslr run tests/fixtures/manual_ux_corpus.csv -c ux_test/config.json -t ux_test/terms.csv -o ux_test/out_es/ -l es
```

**Avaliar**:
- Todas as mensagens estao traduzidas? Ou aparecem chaves cruas (ex.: `progress.processing`)?
- A traducao soa natural ou e literal demais?
- Numeros formatam diferente por locale (1,234 vs 1.234)?

**CHECKPOINT 7** —
- Avaliacao pt_BR (1–5): `_____`
- Avaliacao es (1–5): `_____`
- Chaves nao traduzidas que voce viu: `_____`

---

## CENARIO 8 — Stress / edge cases (15 min)

**Objetivo**: provocar falhas silenciosas reais.

### Passo 8.1 — Corpus vazio

Crie `tests/fixtures/empty.csv`:

```csv
ID,Title,Abstract,Manual Tags
```

(so o cabecalho)

```bash
fastslr run tests/fixtures/empty.csv -c ux_test/config.json -t ux_test/terms.csv -o ux_test/out_empty/
```

**Esperado**: erro **claro** ("corpus vazio") OU sucesso com warning visivel. **Achado F-02**.

**Cole a saida**: `_____`

### Passo 8.2 — terms.csv com regex invalido

Adicione ao `terms.csv`: `AI, positive, [unclosed, 1, all, true`.

```bash
fastslr doctor --input tests/fixtures/manual_ux_corpus.csv -c ux_test/config.json -t ux_test/terms.csv
```

**Esperado**: erro citando linha exata e regex invalido. **Achado F-07**.

**Cole a saida**: `_____`

> **Reverta**: remova a linha invalida.

### Passo 8.3 — Wildcard surpresa

Adicione: `OG, positive, *test*, 5, all, false`.

```bash
fastslr run tests/fixtures/manual_ux_corpus.csv -c ux_test/config.json -t ux_test/terms.csv -o ux_test/out_wild/
```

**Esperado**: sistema aceita `*` como wildcard. Voce sabe disso? **Achado F-08**. O `doctor` ou `run` avisou que `*` e meta?

### Passo 8.4 — BOM em CSV

Salve o `manual_ux_corpus.csv` em UTF-8 **com BOM** (Notepad: "Salvar como" → "UTF-8 with BOM"). Rode `doctor`. **Achado F-10**.

**Cole a saida**: `_____`

### Passo 8.5 — Termos com acentos PT

Adicione: `OG, positive, óleo cru, 2, all, false`. Rode preview. Vai casar com nada na fixture (que e em ingles), mas verifique se o `doctor` aceita o termo sem mangling.

**CHECKPOINT 8** — Quantos dos 5 sub-passos quebraram? `_____ / 5`

---

## CENARIO 9 — Profiles (5 min)

```bash
fastslr profile save my_oilgas_profile -c ux_test/config.json -t ux_test/terms.csv
fastslr profile list
fastslr profile load my_oilgas_profile -o ux_test/restored/
```

**CHECKPOINT 9** —
- Onde os profiles sao guardados?
- Funciona cross-machine? (improvel sem syncing)
- Avaliacao (1–5): `_____`

---

## Sintese final (10 min)

Apos todos os checkpoints, vou (Claude) sintetizar:

### Tabela de avaliacao
| Cenario | Avaliacao | Achados ao vivo |
|---|---|---|
| 1. doctor | __/5 | __ |
| 2. preview | __/5 | __ |
| 3. run | __/5 | __ |
| 4. coverage | __/5 | __ |
| 5. diff | __/5 | __ |
| 6. tui | __/5 | __ |
| 7. i18n | __/5 | __ |
| 8. stress | __/5 | __ |
| 9. profiles | __/5 | __ |

### Top 3 dores de UX descobertas
1. ___
2. ___
3. ___

### Top 3 acertos de UX
1. ___
2. ___
3. ___

### Recomendacao de proximos passos
- Implementar fixes priorizados em [`docs/TEST_PROTOCOL.md` §9](TEST_PROTOCOL.md#9-matriz-de-prioridades).
- Adicionar testes regressivos para cada **achado vivo** confirmado neste roteiro.
- Criar fixture `tests/fixtures/manual_ux_corpus.csv` (deste guia) versionada.

---

## Modo SMOKE (30 min)

Se voce so tem 30 min, rode apenas: **Pre-requisitos → Setup → CENARIO 1 → CENARIO 3 → CENARIO 8.1 e 8.2 → Sintese**. Cobre 80% do valor.

---

## Apendice — Como me reportar achados

Quando algo te surpreender (bom ou ruim), me cole:

1. O comando exato.
2. A saida (stdout + stderr).
3. O que voce **esperava** ver.
4. Por que e relevante (qual decisao do usuario seria melhor com isso?).

Eu entao decido se vira:
- (a) **achado vivo** (atualiza protocolo + escrevemos teste regressivo agora)
- (b) **fix imediato** (codigo + teste no mesmo PR)
- (c) **backlog** (issue/TODO documentado).
