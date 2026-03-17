# Guia de Demonstracao: Variacoes de Configuracao (`triagem.bat`)

## Objetivo

Este guia complementa `docs/LIVE_DEMO_TRIAGEM_BAT.md` com cenarios de demo
para mostrar diferentes comportamentos do launcher, sem alterar codigo.

## Pre-condicoes

- Executar na raiz do projeto.
- Garantir que estes arquivos existem:
  - `data/Final_Corpus.csv`
  - `data/terms_final.csv`
  - `output/resultados_20260108_225947_config.json`

## Base comum (usar em todos os cenarios)

1. `./triagem.bat`
2. Se perguntar sobre perfil, responder `N`.
3. No menu:
   - `21` (reset hard)
   - `25` (restaurar defaults)
   - `1` -> `data/Final_Corpus.csv`
   - `2` -> `data/terms_final.csv`
   - `3` -> `output/resultados_20260108_225947_config.json`

## Cenario 1 - Legado completo com UI rica

Uso: demo principal em tela (barra + resumo + artefatos completos).

- `4` -> `output/demo_cfg_legado_full.xlsx`
- `13` -> `WARNING`
- `18` validar
- `20` executar

Esperado:

- Distribuicao final igual ao legado (`315/147/43`).
- Artefatos completos (`*_academic.md`, `*_bundle.json`, `*_appendix_pack.zip`).

## Cenario 2 - Piloto rapido (amostra)

Uso: demo curta para validar fluxo sem esperar o dataset inteiro.

- `4` -> `output/demo_cfg_piloto_120.xlsx`
- `8` -> `120`
- `9` -> `42`
- `13` -> `INFO`
- `18` validar
- `20` executar

Esperado:

- Execucao mais rapida.
- Em `*_stats.json`: `sample_mode=true`, `sample_size=120`.

## Cenario 3 - Sem pacote appendix (mas com academic/bundle)

Uso: mostrar controle fino dos artefatos de saida.

- `4` -> `output/demo_cfg_sem_appendix.xlsx`
- `11` (toggle `--no-appendix-pack` ON)
- `13` -> `WARNING`
- `18` validar
- `20` executar

Esperado:

- Gera `*_academic.md` e `*_bundle.json`.
- Nao gera `*_appendix_pack.zip`.

## Cenario 4 - Modo enxuto de operacao

Uso: operacao limpa (sem barra, sem output de console, sem pacote academico).

- `4` -> `output/demo_cfg_enxuto.xlsx`
- `7` (toggle `--no-progress` ON)
- `10` (toggle `--no-academic` ON)
- `12` (toggle `--quiet` ON)
- `13` -> `WARNING`
- `18` validar
- `20` executar

Esperado:

- Console quase silencioso durante execucao.
- Sem `*_academic.md`, sem `*_bundle.json`, sem `*_appendix_pack.zip`.

## Validacoes rapidas por cenario

### Conferir distribuicao (cenario 1)

```powershell
$base = Get-Content "output/resultados_20260108_225947_stats.json" -Raw | ConvertFrom-Json
$run  = Get-Content "output/demo_cfg_legado_full_stats.json" -Raw | ConvertFrom-Json
"BASE: " + ($base.decision_distribution | ConvertTo-Json -Compress)
"RUN : " + ($run.decision_distribution  | ConvertTo-Json -Compress)
```

### Conferir flags de amostra (cenario 2)

```powershell
$s = Get-Content "output/demo_cfg_piloto_120_stats.json" -Raw | ConvertFrom-Json
"sample_mode=" + $s.sample_mode
"sample_size=" + $s.sample_size
"population_size=" + $s.population_size
```

### Conferir ausencia de appendix (cenario 3)

```powershell
Test-Path "output/demo_cfg_sem_appendix_appendix_pack.zip"
```

### Conferir ausencia do pacote academico (cenario 4)

```powershell
Test-Path "output/demo_cfg_enxuto_academic.md"
Test-Path "output/demo_cfg_enxuto_bundle.json"
```
