---
tags: [fastslr, validacao, checklist]
---

# ✅ Validação - Checklist

Checklist mestre para garantir que a triagem está **correta, reproduzível e robusta** antes de entregar ao usuário final. Marque os itens conforme forem verificados/corrigidos.

> Detalhes técnicos de cada bug em [[Validação - Bugs e Riscos Conhecidos]]. Cobertura de testes em [[Validação - Estratégia de Testes]].

## 🔥 Correções de lógica prioritárias (Alta)

- [ ] **#1** Unificar thresholds de flag (constants vs presets vs default_config) numa única fonte de verdade + teste de consistência
- [ ] **#2** Substituir parsing frágil de highlights na cobertura (escape robusto / estrutura) + teste com termo contendo aspas
- [ ] **#3** Corrigir falso-positivo de "dead term" (alinhar `original_term` ↔ `m.term`) + teste com termo normalizado que casa

## 🟧 Correções de matching/UX (Média)

- [ ] **#4** Revisar heurística de símbolo na normalização (`c++`, `c#`) e fixar ordem de aplicação + testes
- [ ] **#5** Wildcard `*` cobrir hífen/espaço (`data*` → `data-driven`) + teste
- [ ] **#6** Definir e testar semântica de gap de proximidade; detectar múltiplos separadores
- [ ] **#7** Alinhar default de export `csv` (código `True` vs JSON `false`)
- [ ] **#8** Robustecer detecção de separador de CSV (header score / override)
- [ ] **#9** `run` validar `--terms` ausente com mensagem amigável
- [ ] **#10** `diff` marcar "MISSING" corretamente (`fillna`) + teste de ID em um só lado
- [ ] **#11** `diff` validar coluna de ID em ambos os arquivos antes do merge

## 🟨 Robustez/cosmético (Baixa)

- [ ] **#12** `new_project` não sobrescrever projeto existente sem confirmação/`--force`
- [ ] **#13** `_()` logar warning ao falhar `.format`
- [ ] **#14** Reavaliar `.upper()` no highlight e escapar `***`
- [ ] **#15** Itens menores: `row_num`, `pd.isna` morto, broad-term `>=`, match de ID por string, threshold de `detect_format`, mutação em `browse_terms`

## 🧪 Validação funcional (rodar antes de release)

- [ ] `pytest` — toda a suíte passa (`tests/`)
- [ ] `ruff format` + `ruff check` — zero erros
- [ ] `pyright` (strict) — zero erros
- [ ] `fastslr doctor` em um dataset real → colunas/termos detectados corretamente
- [ ] `fastslr run` em `data/Final_Corpus.csv` com `data/terms_final.csv` → distribuição de decisões plausível
- [ ] Rodar a **mesma** entrada duas vezes → resultados **idênticos** (exceto `run_timestamp`) — prova de determinismo
- [ ] Conferir hashes do `protocol.json` entre execuções idênticas
- [ ] `fastslr coverage` → revisar dead/broad terms (depende de #2/#3 estarem corretos)
- [ ] `fastslr diff v1 v2` → transições corretas (depende de #10/#11)

## 🧷 Casos-limite a verificar (edge cases)

- [ ] CSV só com headers (0 linhas) — ✅ já tratado (regressão #1 do stress test)
- [ ] Artigo sem abstract / sem tags (uplift aplicado?)
- [ ] Artigo sem nenhum termo positivo → `REJECTED` "No positive terms found"
- [ ] Termo com aspas duplas, com `*`, com `c++`/`c#`, regex inválida (`re.error` ignorada?)
- [ ] Encoding não-UTF8 / separador `,` vs `;` vs `\t`
- [ ] IDs duplicados ou numéricos (`1.0` vs `1`)
- [ ] Taxa de erro > `MAX_ERROR_RATE` → run aborta corretamente
- [ ] Política `strict` e `k_of_n` produzem resultados coerentes com a tabela em [[Algoritmo - Políticas de Decisão]]
- [ ] Regra especial: 1 bloco FLAGGED + demais APPROVED com score ≥ 40 → APPROVED_FINAL

## 📋 Pré-publicação acadêmica

- [ ] `protocol.json` gerado e válido (schema v2.1)
- [ ] `academic_package.zip` contém todos os 7 artefatos
- [ ] `config_hash` documentado na publicação
- [ ] Versão (`triage_version`) registrada e consistente

---

Relacionado: [[Validação - Bugs e Riscos Conhecidos]] · [[Validação - Estratégia de Testes]] · [[Home]]
