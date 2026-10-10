# Regressão v3.0.0 → v3.0.1 nos 505 registros históricos

| Campo | Valor |
|---|---|
| **Data** | 2026-10-10 |
| **Para que serve** | Passo 2 do caminho de congelamento da auditoria (`RELATORIO_AUDITORIA.md` §4): toda diferença entre a v3.0.0 e a versão corrigida precisa de causa nomeada antes do congelamento |
| **Comparado** | v3.0.0 (tag `v3.0.0`, commit `f86cc72`) contra a v3.0.1 (correções F01–F10 deste ramo) |
| **Caminho de execução** | Produção: `controller.run_triage` (o mesmo de `fastslr run`), com exportação `.xlsx` pelo `xlsxwriter` que o `config_v8.json` pede |
| **Evidência** | `docs/regressao_v3.0.1/`: scripts (`prepare_inputs.py`, `run_one.py`, `compare.py`, `render.py`) e o detalhe por registro (`regression_detail.json`) |

## 1. Resultado

**Toda diferença tem causa nomeada, e cada uma tem uma causa só.** Nenhum campo de nenhum registro mudou sem que desfazer uma única correção o trouxesse de volta ao valor da v3.0.0.

| Entrada | Decisões v3.0.0 (A / F / R) | Decisões v3.0.1 (A / F / R) | Decisões finais que mudam | Registros com qualquer mudança | Por causa |
|---|---|---|---|---|---|
| Com palavras-chave | 74 / 178 / 253 | 75 / 179 / 251 | 2 (583FSDBK, 847Z9MYF) | 32 | F02: 23 · F01: 5 · F03: 4 |
| Sem palavras-chave | 43 / 149 / 313 | 44 / 154 / 307 | 6 | 20 | F02: 12 · F01: 4 · F03: 4 |

A = APPROVED_FINAL, F = FLAGGED_FINAL, R = REJECTED_FINAL.

- **Toda decisão final que muda sai de REJECTED.** Nenhum registro passa a ser rejeitado: as 2 (com palavras-chave) e as 6 (sem) mudanças de decisão final recuperam registros que a v3.0.0 eliminava.
- **F04 e F06 não mudam nada nos 505**, como a auditoria previu (F04: 0 mudanças; F06: latente, a lista não tem termo regex nem curinga em termo composto).
- **F05:** em todos os casamentos presentes nas duas versões, a linha muda exatamente +2 (2.595 conferidos com palavras-chave e 1.699 sem; 0 exceções).
- **F07–F10** não atuam nesta entrada (IDs `Key` do Zotero, únicos; coluna de palavras-chave presente nas duas variantes; `xlsxwriter` instalado). `input_warnings` sai vazio nas quatro execuções da v3.0.1.

### Conferência com o que a auditoria previu

| Previsto (auditoria §3.1 e §4) | Medido aqui |
|---|---|
| 583FSDBK REJECTED_FINAL → APPROVED_FINAL (F01) | Confirmado, com e sem palavras-chave |
| 847Z9MYF REJECTED_FINAL → FLAGGED_FINAL (F02) | Confirmado, com e sem palavras-chave |
| CSYE4FEP muda só o status (F01, T1A) | Confirmado: T1A REJECTED → APPROVED; a decisão final continua REJECTED (T1C) |
| AG6UCB7U muda só o status (F03, T1A APPROVED → REJECTED) | Confirmado; a decisão final continua REJECTED |
| F02 muda o status de 4 registros | **5**, com palavras-chave: 847Z9MYF, AYKN8CXR, MTHREQFX, C4QDUX56 e **A4S5QRJZ**. A auditoria simulou F02 acrescentando à lista só `machine-learning` e `deep-learning`; a correção no motor vale para todo hífen entre palavras, e A4S5QRJZ ganha `digital twin*` por "Digital-Twin" |
| Toda linha de rastreabilidade +2 (F05) | Confirmado (0 exceções) |
| Nenhuma outra diferença sem causa | 0 campos sem causa; 0 campos que só se explicam por interação de correções |

**Sem palavras-chave há 4 decisões finais a mais que a auditoria não listou** (ela mediu as mudanças de decisão com palavras-chave). Todas saem de REJECTED e têm causa nomeada:

| Registro | Decisão final | Causa | O que casou |
|---|---|---|---|
| A4S5QRJZ | REJECTED → FLAGGED | F02 | "Digital-Twin" → `digital twin*` (T1B L3). Com palavras-chave o registro já era FLAGGED_FINAL e continua |
| 2MFBMTMD | REJECTED → FLAGGED | F01 | "HSE/Safety/Flow assurance" → `flow assurance` (T1A L5); antes, o texto colado "safetyorflow assurance" não casava |
| H4BYTH8R | REJECTED → FLAGGED | F02 | "Digital-twin assisted" → `digital twin*` (T1B L3) |
| MR5HT2NH | REJECTED → FLAGGED | F02 | "GIS-based machine-learning classifiers" → `machine learning` (T1B L1) |

## 2. Método

1. **Entradas.** `prepare_inputs.py` lê o export do Zotero `Final_Corpus.csv` (506 registros), tira `BJ4PZ49E` (nunca triado) e grava os 505 em duas variantes: **com palavras-chave** (o export como está; 308 registros têm *Manual Tags*) e **sem palavras-chave** (coluna *Manual Tags* presente e vazia, como nas rodadas históricas).
2. **Execuções.** `run_one.py` roda `controller.run_triage` com o código escolhido: a extração da tag `v3.0.0` ou o `src/` deste ramo. Um `assert` confere que o pacote importado é o da pasta pedida. Mesmo ambiente para as duas versões, então a diferença vem só do código.
3. **Instrumento.** A execução da v3.0.0 com palavras-chave foi comparada com a linha de base guardada pela auditoria (`evidencia/adjudicacao/run_original.csv`, SHA-256 `5374e641…5a5f`): **0 registros divergentes** em `Status_T0`, `Status_T1A/B/C` e `Final_Decision`. A rodada reproduz a medição da auditoria.
4. **Comparação.** `compare.py` compara as duas saídas célula a célula, menos `run_timestamp` e `triage_version`. Nas colunas de casamento (`Highlights_*`, `AntiHighlights_*`, `Flags_*`) compara o conjunto de casamentos sem o número da linha, e confere à parte que a linha de cada casamento comum muda +2 (F05).
5. **Atribuição de causa (leave-one-out).** Para cada correção F01, F02, F03, F04 e F06, roda-se a v3.0.1 com **só aquela correção desfeita em memória**. Uma correção é causa de um campo que mudou quando desfazê-la devolve o valor da v3.0.0. O campo que nenhuma reversão isolada explicasse seria relatado como interação; não houve nenhum.
   - F01 desfeita: o alvo do símbolo volta a ser colado e a proximidade volta a aceitar componente de uma letra.
   - F02 desfeita: o hífen entre palavras fica.
   - F03 desfeita: o separador volta a `[\s\-/.,]+`.
   - F04 desfeita: a abreviatura volta a casar sem distinção de caixa.
   - F06 desfeita: termo regex volta a gerar proximidade e o `*` volta a ser literal.
6. **Tabelas.** `render.py` gera as tabelas da seção 3 a partir de `regression_detail.json`, sem transcrição manual.

### Identificação

| Item | Valor |
|---|---|
| `Final_Corpus.csv` | SHA-256 `b2235fcb…0caa2`, igual ao `MANIFEST.csv` de `engine_reconstruction` |
| `config_v8.json` | SHA-256 `9ccf61e3…2753e` (cópia byte a byte em `tests/fixtures/historical/`) |
| `terms_final.csv` | SHA-256 `13b99ee2…df25b` (cópia byte a byte em `tests/fixtures/historical/`) |
| Entrada com palavras-chave (505) | SHA-256 `64cbce12…016d4` |
| Entrada sem palavras-chave (505) | SHA-256 `90edacf6…4f0ee` |
| Ambiente | Python 3.12.13; pandas 3.0.6; numpy 2.5.3; openpyxl 3.1.5; xlsxwriter 3.2.9 (as versões do `uv.lock` para Python ≥ 3.11) |

### Reprodução

Com um ambiente do `uv.lock` e a tag `v3.0.0` extraída numa pasta (`git archive v3.0.0 | tar -x -C <pasta_v300>`):

```
python prepare_inputs.py <Final_Corpus.csv> <inputs>
python -I run_one.py <pasta_v300>/src <inputs>/fc505_kw.csv <config_v8.json> <terms_final.csv> <out>/v300_kw
python -I run_one.py <repo>/src      <inputs>/fc505_kw.csv <config_v8.json> <terms_final.csv> <out>/fixed_kw
python -I run_one.py <repo>/src      <inputs>/fc505_kw.csv <config_v8.json> <terms_final.csv> <out>/loo_F01_kw F01
...   (o mesmo para F02, F03, F04, F06 e para fc505_nokw.csv → *_nokw)
python compare.py <out> <run_original.csv> <relatorio>
python render.py <relatorio>/regression_detail.json <inputs>/fc505_kw.csv tabelas.md
```

## 3. Todos os registros que mudam

Ordem: primeiro os que mudam decisão final ou status de bloco, depois só escore, depois só casamentos. "N/E" = NOT_EVALUATED (bloco não avaliado por fail-fast). Escore final = `FinalScore_<bloco>`. Na coluna de casamentos, "+" é casamento ganho na v3.0.1 e "−" é casamento perdido.

Quando um bloco anterior passa a aprovar, o fail-fast deixa de pular o bloco seguinte, que passa a ser avaliado e ganha casamentos próprios (por exemplo, `logistic*` em T1C de 847Z9MYF). Esses casamentos aparecem na linha com a mesma causa do bloco que destravou a avaliação.

### Com palavras-chave

| # | ID | Título (início) | Decisão final | Status por bloco | Escore final | Casamentos | Causa |
|---|---|---|---|---|---|---|---|
| 1 | 583FSDBK | Future Proofing Subsurface Skills During the Energy Transiti | **REJECTED → APPROVED** | T1B: REJECTED → APPROVED; T1C: N/E → APPROVED | T1B: 0 → 10; T1C: 0 → 25 | T1B + `artificial intelligence` (abstract, L1), `machine learning` (abstract, L1)<br>T1C + `supply chain*` (abstract, L1), `supply chain*` (manual_tags, L1) | F01 |
| 2 | 847Z9MYF | Spatial-Temporal Land Loss Modeling and Simulation in a Vuln | **REJECTED → FLAGGED** | T1B: REJECTED → APPROVED; T1C: N/E → FLAGGED | T1B: 0 → 10; T1C: 0 → 6 | T1B + `machine learning` (abstract, L1)<br>T1C + `logistic*` (abstract, L3) | F02 |
| 3 | A4S5QRJZ | OPERATIONS OPTIMISATION OF A GAS-LIFT COMPRESSION SYSTEM USI | igual | T1B: FLAGGED → APPROVED | T1B: 11 → 29 | T1B + `digital twin*` (abstract, L3), `digital twin*` (title, L3) | F02 |
| 4 | AG6UCB7U | A Comprehensive Survey of Industry 4.0, IIoT and Areas of Im | igual | T1A: APPROVED → REJECTED; T1B: REJECTED → N/E | T1A: 10 → 0; T1B: 9 → 0 | T1A − `oil and gas` (abstract, L1, prox.)<br>T1B − `industry 4.0` (abstract, L5), `industry 4.0` (manual_tags, L5), `industry 4.0` (title, L5) | F03 |
| 5 | AYKN8CXR | Real-Time Fluid Identification From Integrating Advanced Mud | igual | T1B: REJECTED → APPROVED; T1C: N/E → REJECTED | T1B: 0 → 11.7 | T1B + `machine learning` (abstract, L1) | F02 |
| 6 | C4QDUX56 | Reservoir Fluid Data Acquisition Using Advanced Mud-Logging  | igual | T1B: REJECTED → APPROVED; T1C: N/E → REJECTED | T1B: 0 → 11.7 | T1B + `machine learning` (abstract, L1) | F02 |
| 7 | CSYE4FEP | Drilling in the Fourth Industrial Revolution—Vision and Chal | igual | T1A: REJECTED → APPROVED; T1B: N/E → APPROVED; T1C: N/E → REJECTED | T1A: 0 → 10; T1B: 0 → 40 | T1A + `oil and gas` (abstract, L1, prox.)<br>T1B + `artificial intelligence` (abstract, L1), `artificial intelligence` (manual_tags, L1), `digital twin*` (abstract, L3), `digital twin*` (manual_tags, L3) | F01 |
| 8 | MTHREQFX | Reservoir Fluid Typing From Standard Mud Gas – A Machine-Lea | igual | T1B: REJECTED → APPROVED; T1C: N/E → REJECTED | T1B: 0 → 35.1 | T1B + `machine learning` (abstract, L1), `machine learning` (title, L1) | F02 |
| 9 | 2MFBMTMD | Flow Back Optimization in Deep Water in Presence of Solids - | igual | igual | T1A: 22 → 24 | T1A + `flow assurance` (abstract, L5) | F01 |
| 10 | 2VGENLN3 | Technology predictions for arctic hydrocarbon development: D | igual | igual | T1A: 10 → 25 | T1A + `oil and gas` (manual_tags, L1), `oil and gas` (manual_tags, L1, prox.) | F01 |
| 11 | 3RF6PZ3F | Delivering best-in-class shallow water wellhead platform, an | igual | igual | T1B: 10 → 25 | T1B + `machine learning` (manual_tags, L1) | F02 |
| 12 | 4Z6UT3WQ | China Offshore Intelligent Oilfield Production Monitoring Sy | igual | igual | T1A: 58 → 52 | T1A − `exploration and production` (abstract, L3, prox.) | F03 |
| 13 | 8AQNUNGQ | Advanced Machine Learning for Accurate Reservoir Characteriz | igual | igual | T1B: 42 → 57 | T1B + `machine learning` (manual_tags, L1) | F02 |
| 14 | AGDQ4M6K | Machine-Learning-Based Classification for Pipeline Corrosion | igual | igual | T1B: 25 → 45 | T1B + `machine learning` (title, L1) | F02 |
| 15 | EIKXVHD4 | Driving Profitability in Oil and Gas production Operations b | igual | igual | T1A: 45 → 53 | T1A + `E&P` (abstract, L2) | F01 |
| 16 | EJJ7UU2F | A Machine-Learning Approach to Predict Gas-Oil Ratio Based o | igual | igual | T1B: 11.7 → 35.1 | T1B + `machine learning` (title, L1) | F02 |
| 17 | H4BYTH8R | Digital-twin assisted: Fault diagnosis using deep transfer l | igual | igual | T1B: 24 → 42 | T1B + `digital twin*` (abstract, L3), `digital twin*` (title, L3) | F02 |
| 18 | MR5HT2NH | Spatial assessment of gross vertical reservoir heterogeneity | igual | igual | T1B: 15 → 45 | T0 flag + `case studies` (manual_tags)<br>T1B + `machine learning` (abstract, L1), `machine learning` (title, L1) | F02 |
| 19 | NVCBUH9R | Machine Learning Models to Automatically Validate Petroleum  | igual | igual | T1A: 65 → 55 | T1A − `oil and gas` (abstract, L1, prox.) | F03 |
| 20 | PAJ2CN35 | Private 5G Practice in Oil and Gas Industry | igual | igual | T1A: 51 → 45 | T1A − `exploration and production` (abstract, L3, prox.) | F03 |
| 21 | PJUVYGVX | Applying Machine Learning to the Fuel Theft Problem on Pipel | igual | igual | T1B: 35 → 45 | T1B + `machine learning` (abstract, L1) | F02 |
| 22 | 6DQBDDHY | Robot Field Development Teams: Harnessing Multi-Agent Artifi | igual | igual | igual | T0 flag + `case studies` (manual_tags) | F02 |
| 23 | EXI7PNPH | Quantifying Tail Risk Spillovers in Chinese Petroleum Supply | igual | igual | igual | T1B + `neural network*` (abstract, L1), `neural network*` (title, L1) | F02 |
| 24 | IGRIBGAI | A multi-level classification model for corrosion defects in  | igual | igual | igual | T1A + `oil and gas` (manual_tags, L1) | F02 |
| 25 | KBC56IP8 | Electronic Prognostics Innovations for Applications to Aeros | igual | igual | igual | T1A + `oil and gas` (abstract, L1) | F02 |
| 26 | MVZ2VK5D | Using artificial intelligence to find design errors in the e | igual | igual | igual | T1B + `machine learning` (manual_tags, L1) | F02 |
| 27 | NH9XDV2K | Interpretable Cross Value Chain Decision Support Model: A Co | igual | igual | igual | T1C flag + `value chain` (manual_tags) | F02 |
| 28 | SFJ2IP4I | Lithofacies Classification of Carbonate Reservoirs Using Adv | igual | igual | igual | T0 flag + `case studies` (manual_tags) | F02 |
| 29 | SIU99MSW | FlexDelivery - Integrated Logistics in the Offshore Sector | igual | igual | igual | T0 flag + `case studies` (manual_tags) | F02 |
| 30 | VJR9Y35T | Reliable deep learning framework for the ground penetrating  | igual | igual | igual | T1B + `machine learning` (manual_tags, L1) | F02 |
| 31 | VVAYMR24 | Advancing Decision Making In Field Operations And Maintenanc | igual | igual | igual | T0 flag + `case studies` (manual_tags) | F02 |
| 32 | W5KLZV5H | DYNAMIC PLACEMENT OF RAPIDLY DEPLOYABLE MOBILE SENSOR ROBOTS | igual | igual | igual | T0 flag + `case studies` (manual_tags) | F02 |

### Sem palavras-chave

| # | ID | Título (início) | Decisão final | Status por bloco | Escore final | Casamentos | Causa |
|---|---|---|---|---|---|---|---|
| 1 | 2MFBMTMD | Flow Back Optimization in Deep Water in Presence of Solids - | **REJECTED → FLAGGED** | T1A: REJECTED → FLAGGED; T1B: N/E → FLAGGED; T1C: N/E → FLAGGED | T1A: 4.68 → 7.02; T1B: 0 → 9.36; T1C: 0 → 7.02 | T1A + `flow assurance` (abstract, L5)<br>T1B + `optimization algorithm*` (abstract, L2)<br>T1C + `logistic*` (abstract, L3) | F01 |
| 2 | 583FSDBK | Future Proofing Subsurface Skills During the Energy Transiti | **REJECTED → APPROVED** | T1B: REJECTED → APPROVED; T1C: N/E → APPROVED | T1B: 0 → 11.7; T1C: 0 → 11.7 | T1B + `artificial intelligence` (abstract, L1), `machine learning` (abstract, L1)<br>T1C + `supply chain*` (abstract, L1) | F01 |
| 3 | 847Z9MYF | Spatial-Temporal Land Loss Modeling and Simulation in a Vuln | **REJECTED → FLAGGED** | T1B: REJECTED → APPROVED; T1C: N/E → FLAGGED | T1B: 0 → 11.7; T1C: 0 → 7.02 | T1B + `machine learning` (abstract, L1)<br>T1C + `logistic*` (abstract, L3) | F02 |
| 4 | A4S5QRJZ | OPERATIONS OPTIMISATION OF A GAS-LIFT COMPRESSION SYSTEM USI | **REJECTED → FLAGGED** | T1B: REJECTED → APPROVED; T1C: N/E → FLAGGED | T1B: 2.34 → 23.4; T1C: 0 → 7.02 | T1B + `digital twin*` (abstract, L3), `digital twin*` (title, L3)<br>T1C + `lead time*` (abstract, L3) | F02 |
| 5 | AG6UCB7U | A Comprehensive Survey of Industry 4.0, IIoT and Areas of Im | igual | T1A: APPROVED → REJECTED; T1B: REJECTED → N/E | T1A: 11.7 → 0; T1B: 7.02 → 0 | T1A − `oil and gas` (abstract, L1, prox.)<br>T1B − `industry 4.0` (abstract, L5), `industry 4.0` (title, L5) | F03 |
| 6 | AYKN8CXR | Real-Time Fluid Identification From Integrating Advanced Mud | igual | T1B: REJECTED → APPROVED; T1C: N/E → REJECTED | T1B: 0 → 11.7 | T1B + `machine learning` (abstract, L1) | F02 |
| 7 | C4QDUX56 | Reservoir Fluid Data Acquisition Using Advanced Mud-Logging  | igual | T1B: REJECTED → APPROVED; T1C: N/E → REJECTED | T1B: 0 → 11.7 | T1B + `machine learning` (abstract, L1) | F02 |
| 8 | CSYE4FEP | Drilling in the Fourth Industrial Revolution—Vision and Chal | igual | T1A: REJECTED → APPROVED; T1B: N/E → APPROVED; T1C: N/E → REJECTED | T1A: 0 → 11.7; T1B: 0 → 18.72 | T1A + `oil and gas` (abstract, L1, prox.)<br>T1B + `artificial intelligence` (abstract, L1), `digital twin*` (abstract, L3) | F01 |
| 9 | H4BYTH8R | Digital-twin assisted: Fault diagnosis using deep transfer l | **REJECTED → FLAGGED** | T1B: REJECTED → APPROVED; T1C: N/E → FLAGGED | T1B: 0 → 21.06; T1C: 0 → 7.02 | T1B + `digital twin*` (abstract, L3), `digital twin*` (title, L3)<br>T1C + `logistic*` (abstract, L3) | F02 |
| 10 | MR5HT2NH | Spatial assessment of gross vertical reservoir heterogeneity | **REJECTED → FLAGGED** | T1B: REJECTED → APPROVED; T1C: N/E → FLAGGED | T1B: 0 → 35.1; T1C: 0 → 7.02 | T1B + `machine learning` (abstract, L1), `machine learning` (title, L1)<br>T1C + `logistic*` (abstract, L3) | F02 |
| 11 | MTHREQFX | Reservoir Fluid Typing From Standard Mud Gas – A Machine-Lea | igual | T1B: REJECTED → APPROVED; T1C: N/E → REJECTED | T1B: 0 → 35.1 | T1B + `machine learning` (abstract, L1), `machine learning` (title, L1) | F02 |
| 12 | 4Z6UT3WQ | China Offshore Intelligent Oilfield Production Monitoring Sy | igual | igual | T1A: 46.8 → 39.78 | T1A − `exploration and production` (abstract, L3, prox.) | F03 |
| 13 | AGDQ4M6K | Machine-Learning-Based Classification for Pipeline Corrosion | igual | igual | T1B: 11.7 → 35.1 | T1B + `machine learning` (title, L1) | F02 |
| 14 | EIKXVHD4 | Driving Profitability in Oil and Gas production Operations b | igual | igual | T1A: 35.1 → 44.46 | T1A + `E&P` (abstract, L2) | F01 |
| 15 | EJJ7UU2F | A Machine-Learning Approach to Predict Gas-Oil Ratio Based o | igual | igual | T1B: 11.7 → 35.1 | T1B + `machine learning` (title, L1) | F02 |
| 16 | NVCBUH9R | Machine Learning Models to Automatically Validate Petroleum  | igual | igual | T1A: 44.46 → 32.76 | T1A − `oil and gas` (abstract, L1, prox.) | F03 |
| 17 | PAJ2CN35 | Private 5G Practice in Oil and Gas Industry | igual | igual | T1A: 42.12 → 35.1 | T1A − `exploration and production` (abstract, L3, prox.) | F03 |
| 18 | PJUVYGVX | Applying Machine Learning to the Fuel Theft Problem on Pipel | igual | igual | T1B: 23.4 → 35.1 | T1B + `machine learning` (abstract, L1) | F02 |
| 19 | EXI7PNPH | Quantifying Tail Risk Spillovers in Chinese Petroleum Supply | igual | igual | igual | T1B + `neural network*` (abstract, L1), `neural network*` (title, L1) | F02 |
| 20 | KBC56IP8 | Electronic Prognostics Innovations for Applications to Aeros | igual | igual | igual | T1A + `oil and gas` (abstract, L1) | F02 |

## 4. O que a regressão mostra além do esperado

### 4.1 F03 também tira casamentos plausíveis

Nos 505, o separador sem ponto e vírgula tirou 4 casamentos de proximidade. Um era espúrio; três eram plausíveis:

| Registro | Texto | Casamento perdido | Juízo |
|---|---|---|---|
| AG6UCB7U | "industries such as food, oil, natural gas" | `oil and gas` | Espúrio: é o caso que motivou F03 |
| 4Z6UT3WQ | "petroleum exploration, production decisions" | `exploration and production` | Plausível |
| PAJ2CN35 | "hydrocarbons exploration, production, refining" | `exploration and production` | Plausível |
| NVCBUH9R | "multiphase mixture composed of oil, water, and gas" | `oil and gas` | Plausível |

Nenhum dos três plausíveis mudou status, porque esses registros tinham outra evidência de O&G. Numa coleção nova, um registro cuja **única** evidência de contexto seja uma lista com vírgula perde esse casamento e pode ser rejeitado; pela D-01, sairia sem retriagem. A auditoria escolheu esse custo para cortar os casamentos espúrios. A decisão fica na fase P0, junto com P4: aceitar o separador `[\s\-/]+` ou cadastrar as formas de lista que importam como termo próprio (`exploration, production` casa como frase exata).

### 4.2 Bloco destravado expõe um termo amplo

Quando F01 ou F02 faz um bloco aprovar, o bloco seguinte passa a ser avaliado. Em T1C isso expôs `logistic*` casando "logistic regression" (método estatístico) em 847Z9MYF e MR5HT2NH; em H4BYTH8R o mesmo termo casa "industry logistics", que é o sentido pretendido. O efeito é sinalizar, não aprovar, e o defeito é da lista de termos, não do motor: entra na revisão da lista na fase P0.

### 4.3 Hífen também alcança anti-termos e sinalizadores

F02 vale para todos os termos. Nos 505, as palavras-chave "Case-studies" passaram a acionar o sinalizador global `case studies` (6 registros) e "Cross value-chain" o sinalizador `value chain` de T1C (NH9XDV2K). Nenhum desses casamentos mudou status. É o comportamento pretendido: a grafia com hífen é a mesma expressão.

## 5. Versão proposta: 3.0.1

`VERSION` neste ramo já está em `3.0.1`, para que todo artefato gerado (`triage_version`, `protocol.json`) se distinga da v3.0.0 auditada. Nada foi marcado com tag nem publicado.

- **Por que patch:** as dez mudanças corrigem defeitos contra o comportamento documentado (o `TECHNICAL.md` já dava `\s+` como separador; a auditoria classificou cada uma como defeito). Não há recurso novo.
- **Por que não 3.1.0:** segundo a nota de divergência de clones, existe uma `v3.1.0` nunca publicada noutro clone (máquina Leonardo). Reusar o número confundiria os dois pacotes.
- **Alternativa defensável:** 3.2.0, se Leonardo preferir sinalizar que a entrada passou a ser recusada em casos antes aceitos (F08) e que a coluna `row=` mudou de numeração (F05). Nunca 3.1.0.

**No lançamento** (só com o OK de Leonardo): trocar `v3.0.0`/`==3.0.0` por `3.0.1` no título e nos comandos de instalação do `README.md` e do `docs/GUIA_DO_USUARIO.md`, datar a seção `[3.0.1]` do `CHANGELOG.md`, criar a tag e publicar. Até lá esses textos continuam apontando para a versão publicada.

## 6. Pendências fora do motor

| Item | Situação | Ação |
|---|---|---|
| `tests/test_tui_smoke.py::test_dashboard_button_press_navigates` intermitente | Já existia no `HEAD` sem estas mudanças (1 falha em 5 execuções). Causa: corrida interna do `textual` 8.2.8, `Header.set_title` consulta `HeaderTitle` durante a troca de tela e levanta `NoMatches` | Tarefa separada; não toca o motor |
| Fixtures `tests/fixtures/historical/` | `config_v8.json` e `terms_final.csv` entram no repositório, que é público. O commit #7 tirou `data/*.csv` por ser corpus de terceiros; estes dois arquivos são a configuração da RSL, sem texto de terceiros | Leonardo decide antes do push |
| Notas do vault (`Algoritmo - Normalização`, `Algoritmo - Padrões e Proximidade`) | Descrevem o comportamento da v3.0.0 (abreviatura sem caixa, separador com vírgula) | Não editadas aqui: o vault é junção do Obsidian |
| Ponto de entrada `fastslr = fastslr.app.cli:app` | Não passa por `cli.main()`, que traduz `ValueError` em mensagem curta. `run` e `doctor` tratam F08 por conta própria; `preview` e `coverage` com ID repetido saem com código 1 e traceback | Item separado |
