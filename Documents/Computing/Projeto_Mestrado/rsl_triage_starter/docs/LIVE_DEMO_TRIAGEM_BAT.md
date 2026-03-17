# Roteiro de Demo ao Vivo (`triagem.bat`)

## Objetivo

Demonstrar, em tela, que o launcher em `.bat`:

- abre de forma estavel,
- mostra progresso/statuses legiveis,
- executa o fluxo legado sem divergencia de resultado final.

## Pre-condicoes

- Estar na raiz do projeto.
- Arquivos de referencia presentes:
  - `data/Final_Corpus.csv`
  - `data/terms_final.csv`
  - `output/resultados_20260108_225947_config.json`
  - `output/resultados_20260108_225947_stats.json`

## Demo principal (UI/menu)

1. Abrir terminal na raiz e executar:

```powershell
./triagem.bat
```

2. Se aparecer pergunta de perfil, responder `N`.

3. No menu, executar exatamente:

- `21` (reset hard)
- `25` (restaurar defaults)
- `1` -> `data/Final_Corpus.csv`
- `2` -> `data/terms_final.csv`
- `3` -> `output/resultados_20260108_225947_config.json`
- `4` -> `output/validacao_legado_menu.xlsx`
- `13` -> `WARNING`
- `18` (validar config)
- `19` (preview comando)
- `20` (executar)

4. Durante a execucao, destacar:

- barra de progresso,
- passos `[PASSO 1/4]`, `[PASSO 2/4]`, `[PASSO 3/4]`,
- resumo final com distribuicao.

5. Ao terminar, pressionar `Enter` e depois `0` para sair.

## Validacao rapida de equivalencia

Executar no PowerShell:

```powershell
$base = Get-Content "output/resultados_20260108_225947_stats.json" -Raw | ConvertFrom-Json
$menu = Get-Content "output/validacao_legado_menu_stats.json" -Raw | ConvertFrom-Json
"BASE: " + ($base.decision_distribution | ConvertTo-Json -Compress)
"MENU: " + ($menu.decision_distribution | ConvertTo-Json -Compress)
if (($base.decision_distribution | ConvertTo-Json -Compress) -eq ($menu.decision_distribution | ConvertTo-Json -Compress)) {
  "STATUS: OK (equivalente ao legado)"
} else {
  "STATUS: DIFF"
}
```

Esperado: `REJECTED_FINAL=315`, `FLAGGED_FINAL=147`, `APPROVED_FINAL=43`.

## Plano B (execucao direta sem menu)

Se precisar demonstrar fallback rapido:

```powershell
./triagem.bat -i data/Final_Corpus.csv -t data/terms_final.csv -c output/resultados_20260108_225947_config.json -o output/validacao_legado_replay.xlsx --log-level WARNING
```
