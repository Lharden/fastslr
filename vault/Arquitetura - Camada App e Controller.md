---
tags: [fastslr, arquitetura, app, controller]
---

# 🖥️ Arquitetura - Camada App e Controller

A camada `app/` é a interface com o usuário. Ela **nunca** acessa o domínio diretamente — toda regra passa por `controller.py`.

## `controller.py` — a fachada (a peça mais importante)

É a **única ponte** entre interface e core. Toda função da CLI/TUI chama o controller, que orquestra os módulos do core.

Pipeline central — `_prepare_config()`:
```
load_config(config.json)
  → parse_terms_csv(terms.csv/xlsx)        # valida e estrutura termos
  → NormalizationEngine(regras)
  → precompile_patterns(bloco, engine)     # para cada bloco + T0
```
Depois, `run_triage()` chama `process_articles()` do [[Arquitetura - Camada Core|engine]] e grava resultados via `io`.

Outras funções: `validate_config`, `inspect_run_setup` (alimenta o `doctor`), `preview_triage`, `analyze_coverage`, `diff_results`, `create_project`, `browse_terms`, `export_academic_package`.

> [!warning] Pontos de atenção no controller
> Vários riscos de robustez estão concentrados aqui (validação de `--terms` ausente, `diff` com merge `outer` que não marca "MISSING" corretamente, `new_project` que sobrescreve sem confirmar). Ver itens em [[Validação - Bugs e Riscos Conhecidos]].

## `cli.py` — front-end de linha de comando (Typer + Rich)

Comandos: `version`, `doctor`, `run`, `preview`, `coverage`, `diff`, `new-project`, `export`, `terms`, `tui`, e o subgrupo `profile` (`save`/`load`/`list`).

- Importa o controller **lazy** (dentro de cada função) — bom para tempo de boot.
- `run` valida existência de `input` e `config`, executa `validate_config`, bloqueia em erros e **confirma warnings interativamente**, com barra de progresso Rich.

## `tui.py` — interface no terminal (Textual)

10 telas: New Project, Load Profile, Edit Configuration, Browse Terms, Run Triage, Results Explorer, Coverage Analysis, Compare Runs, Export Package, Settings & Language. Todas operam **através do controller**.

## `i18n/__init__.py` — internacionalização

- `set_locale(name)` — match exato ou por prefixo (`pt` → `pt_BR`); fallback `en`.
- `detect_locale()` — `FASTSLR_LANG` env → locale do SO → `en`.
- `_(key, **kwargs)` — lookup locale ativo → fallback `en` → a própria chave; `.format()` com `except (KeyError, IndexError): pass`.
- Locales: `en.json`, `pt_BR.json`, `es.json`. **Só a interface é traduzida** — dados de saída ficam em inglês (decisão D4).

> [!warning] Falha silenciosa de tradução
> Se uma string traduzida tiver placeholder com nome errado, o `_()` retorna o template **sem substituir**, sem erro visível. Ver item em [[Validação - Bugs e Riscos Conhecidos]].

## `profiles.py` — perfis de configuração

CRUD de perfis em `~/.fastslr/profiles/*.json` (`Path.home()`, cross-platform). `save_profile`, `load_profile`, `list_profiles`, `delete_profile`.

## `__main__.py`

Entry point de `python -m fastslr`: importa `app` de `cli.py` e o invoca.

---

Relacionado: [[Arquitetura - Visão Geral]] · [[Arquitetura - Camada Core]] · [[Fluxo de Dados]] · [[Home]]
