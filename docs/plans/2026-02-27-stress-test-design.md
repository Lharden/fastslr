# Stress Test & Failure Analysis — AI Pipeline v2.1

**Data:** 2026-02-27
**Escopo:** Analise completa de cenarios de falha + design de correcoes

---

## Bugs Confirmados (reproduzidos)

### BUG-1: `auto` mode re-parse crash [CRITICA]
- **Linha:** 1630 — `return main(argv=None if argv is None else [task])`
- **Cenario:** `aip auto "fix typo"` → NLU classifica como `pipeline` → `main(None)` re-parseia `sys.argv` → argparse crash
- **Fix:** Sempre passar `[task]`: `return main([task])`

### BUG-2: `_extract_json()` falha com JSON aninhado [ALTA]
- **Linha:** 1172 — regex `r"\{[^{}]*\}"` exclui braces internos
- **Cenario:** JSON com objetos aninhados → captura sub-objeto em vez do raiz
- **Fix:** Usar `json.JSONDecoder().raw_decode()` com busca iterativa

### BUG-3: Windows 32k command line limit [CRITICA]
- **Linhas:** 382, 421, 786 — prompts longos como args de subprocess
- **Cenario:** Plan > 30k chars → `OSError: [WinError 206]` no Windows
- **Fix:** Escrever prompt em tempfile e passar via stdin pipe ao subprocess

### BUG-4: Double `logging.basicConfig()` [MEDIA]
- **Linhas:** 1007 + 1529 — ambos `main()` e `entry_point()` configuram logging
- **Cenario:** Segunda chamada e no-op → `-v` pode nao funcionar
- **Fix:** Centralizar em `_setup_logging(verbose)` chamada uma unica vez

---

## Categorias de Falha

### Cat-1: Subprocess sem timeout (hang forever)
- **Funcoes:** `run_ask`, `run_chat`, `run_plan`, `run_explore`
- **Fix:** Adicionar timeout configuravel + try/except TimeoutExpired

### Cat-2: Git assume repo existente
- **Fix:** Check `git rev-parse --git-dir` no inicio, warn loudly

### Cat-3: `git add -A` commita secrets
- **Linha:** 686
- **Fix:** Usar `git add -u` (so tracked files)

### Cat-4: `base_branch` hardcoded "main"
- **Fix:** Auto-detectar branch default do remote

### Cat-5: `_substitute_env_vars` ignora listas
- **Fix:** Adicionar `elif isinstance(value, list)` recursivo

### Cat-6: Prompt template faltando = execucao silenciosa
- **Fix:** Raise error ou usar fallback prompt embutido

### Cat-7: Acumulo de runs sem cleanup
- **Fix:** TTL automatico ou `--cleanup-runs --keep N`

---

## Ordem de Implementacao

1. BUG-1 (auto crash) — 1 linha
2. BUG-4 (logging) — ~15 linhas
3. BUG-3 (Win32k) — ~40 linhas (stdin pipe)
4. BUG-2 (_extract_json) — ~15 linhas
5. Cat-1 (timeouts) — ~30 linhas
6. Cat-2 (git check) — ~15 linhas
7. Cat-3 (git add -u) — 1 linha
8. Cat-4 (base branch) — ~15 linhas
9. Cat-5 (env vars lists) — ~5 linhas
10. Cat-6 (prompt fallback) — ~10 linhas
11. Cat-7 (cleanup) — ~30 linhas

**Total estimado:** ~180 linhas novas/modificadas
