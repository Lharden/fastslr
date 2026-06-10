# Spec Light - Continuidade da Auditoria Final Pre-IP

**Data:** 2026-06-10  
**Estado:** Checkpoint humano #1 aprovado; Fase 4 em execucao  
**Baseline:** `2fb2ea0ab4187e814637c6f54df5a6d66cbcb1a5`

## Objetivo

Retomar a auditoria final iniciada pelo Claude Fable 5, validar adversarialmente os
findings brutos, corrigir os itens aprovados com TDD e produzir evidencias para o
registro de propriedade intelectual, sem publicar no PyPI.

## Requisitos

- **REQ-001:** Preservar e documentar o trabalho anterior com evidencia verificavel.
- **REQ-002:** Filtrar findings contra o Filtro-70 e deduplicar causas-raiz.
- **REQ-003:** Nao aplicar mudancas de decisao de triagem ou formato de output sem
  aprovacao humana item a item.
- **REQ-004:** Aplicar correcoes aprovadas com teste de regressao antes do codigo.
- **REQ-005:** Verificar pytest, Ruff, Pyright, determinismo, build, sdist/wheel e
  smoke test antes de commit/tag local.

## Acceptance Criteria

- **AC-001:** Given o estado deixado pelo Claude, when a retomada e concluida, then
  os artefatos e atividades anteriores sao identificados e separados do trabalho novo.
- **AC-002:** Given os 58 findings brutos, when a verificacao adversarial termina,
  then cada finding possui veredito e pertence a uma causa-raiz canonica.
- **AC-003:** Given um fix que altera decisao ou output, when a implementacao e
  considerada, then ela permanece bloqueada ate aprovacao explicita do Leonardo.
- **AC-004:** Given um fix aprovado, when ele e implementado, then existe ciclo TDD
  red-green e os gates completos permanecem verdes.
- **AC-005:** Given a versao candidata pre-IP, when a verificacao final termina, then
  ha relatorio rastreavel, snapshot, hash e tag local, sem publicacao remota.

## Boundaries

- **ALWAYS:** Usar Python, pytest, Ruff e Pyright; preservar determinismo.
- **ALWAYS:** Registrar evidencias e distinguir confirmado, rebaixado, duplicado e
  refutado.
- **NEVER:** Publicar no PyPI/GitHub Release durante esta auditoria.
- **NEVER:** Alterar decisoes ou formato de output sem checkpoint item a item.
- **ASK:** Dados oficiais de autoria, afiliacao, titularidade e autorizacao da tag.

## Estado Atual

- Fases 0 e 1 do plano anterior: concluidas.
- Fase 2, verificacao adversarial: concluida nesta retomada.
- Fase 3, triagem e Checkpoint humano #1: concluida e aprovada.
- Fase 4: em execucao.
- Fases 5 e 6: pendentes.
