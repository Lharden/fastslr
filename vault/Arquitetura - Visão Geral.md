---
tags: [fastslr, arquitetura]
---

# 🏛️ Arquitetura - Visão Geral

FastSLR adota uma arquitetura em **duas camadas** com uma **fachada** entre elas.

```
┌──────────────────────────────────────────────────────────┐
│                    CAMADA APP (app/)                       │
│   cli.py (Typer)   tui.py (Textual)   i18n/   profiles.py  │
└───────────────────────────┬──────────────────────────────┘
                            │  (única ponte)
                ┌───────────▼────────────┐
                │   controller.py         │  ← FACHADA
                │  (orquestra o core)     │
                └───────────┬────────────┘
                            │
┌───────────────────────────▼──────────────────────────────┐
│                   CAMADA CORE (core/)                      │
│  engine → scoring → patterns → normalization → config     │
│           models · constants · io · coverage · adapters   │
└──────────────────────────────────────────────────────────┘
```

## Regra de dependência

- `app/cli.py` e `app/tui.py` **nunca** importam `core` diretamente. Tudo passa por [[Arquitetura - Camada App e Controller|controller.py]].
- O `core/` **não conhece** o `app/`. É uma biblioteca pura, usável programaticamente (ver "Uso Programático" no `README.md`).
- Dentro do core, a ordem de dependência é: `config` → `patterns` → `normalization` → `scoring` → `engine`. `models` e `constants` são folhas.

## Decisões de arquitetura (decision log)

Do `docs/plans/fastslr-v3-decision-log.md`:

| ID | Decisão | Porquê |
|----|---------|--------|
| **D1** | Remover IA por completo | Publicação acadêmica exige sistema 100% mecânico. Histórico preservado no Git. |
| **D2** | CLI batch + TUI interativa | Batch p/ reprodutibilidade e scripting; TUI p/ uso guiado por não-programadores. |
| **D3** | Arquitetura híbrida (motor v2.0 + nova shell) | O risco está na shell, não no algoritmo testado. O engine v2.0 é mantido quase intacto. |
| **D4** | i18n só na interface; dados em inglês | Garante reprodutibilidade entre locales. |
| **D6** | Distribuição cross-platform via pip | Acessível a não-programadores. |
| **D8** | Licença MIT | Uso acadêmico aberto. |
| **D10** | Bump major v3.0.0 | Mudanças incompatíveis com versões anteriores. |
| **D11** | pyright strict + ruff + stress tests | Qualidade de código verificável. |

> [!warning] Premissa "engine intocado" vs. realidade
> O design afirma que a **única** mudança no engine foi trocar `ProgressBar` por um callback `on_progress`. Porém, o **Finding #1** do stress test (CSV vazio) modificou `core/io.py` durante o *hardening* (Fase 7). Ou seja, o motor **foi** tocado. Detalhe em [[Validação - Bugs e Riscos Conhecidos]].

## Estrutura de pastas

```
src/fastslr/
├── core/        # motor de triagem (lógica de domínio)
│   ├── engine.py          # pipeline: process_articles()
│   ├── scoring.py         # matching, avaliação de bloco, decisão final
│   ├── patterns.py        # compilação de regex, proximidade
│   ├── normalization.py   # abreviações, variantes, símbolos
│   ├── config.py          # carga de config + parsing de termos
│   ├── models.py          # dataclasses (BlockEvaluation, GlobalParams…)
│   ├── constants.py       # defaults e constantes
│   ├── io.py              # CSV/XLSX, highlight, protocol, ZIP
│   ├── coverage.py        # análise de cobertura de termos
│   ├── adapters.py        # importadores Zotero/Scopus/WoS
│   └── presets.py         # presets de níveis e scaffolding
├── app/         # interface
│   ├── cli.py             # comandos (Typer + Rich)
│   ├── controller.py      # FACHADA app↔core
│   ├── tui.py             # interface no terminal (Textual)
│   └── profiles.py        # perfis em ~/.fastslr/profiles/
└── i18n/        # locales en / pt_BR / es
```

---

Relacionado: [[Arquitetura - Camada Core]] · [[Arquitetura - Camada App e Controller]] · [[Fluxo de Dados]] · [[Home]]
