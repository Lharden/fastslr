---
tags: [fastslr, arquitetura, fluxo]
---

# 🔄 Fluxo de Dados

Da exportação bibliográfica ao pacote acadêmico reproduzível.

```
┌─────────────┐   ┌──────────────┐   ┌───────────────┐
│ artigos.csv │   │ config.json  │   │ terms.csv/xlsx│
│ (Zotero/    │   │ (parâmetros) │   │ (termos por   │
│  Scopus/WoS)│   │              │   │  bloco)       │
└──────┬──────┘   └──────┬───────┘   └───────┬───────┘
       │                 │                   │
       ▼                 ▼                   ▼
  load_table_safe   load_config        parse_terms_csv
  (io.py)           (config.py)        (config.py)
       │                 └─────────┬─────────┘
       │                           ▼
       │                   _prepare_config (controller)
       │              NormalizationEngine + precompile_patterns
       │                           │
       └───────────┬───────────────┘
                   ▼
         process_articles (engine.py)
   ┌───────────────────────────────────────┐
   │  por artigo:                           │
   │   T0 → blocos (fail-fast) → decisão    │
   └───────────────────┬───────────────────┘
                       ▼
              result_df + stats
                       │
       ┌───────────────┼────────────────────────┐
       ▼               ▼                         ▼
 triage_results.xlsx  triage_report.txt   academic_package.zip
 (scores, status,     (estatísticas)      (protocol.json +
  highlights,                              hashes SHA-256 +
  Final_Decision)                          relatórios)
```

## Etapas

1. **Carga de entrada** — `io.load_table_safe` detecta encoding (opcional via `chardet`) e separador (`;`, `,`, `\t`), lê CSV/XLSX. `adapters.py` reconhece o formato (Zotero/Scopus/WoS) e renomeia colunas.
2. **Auto-mapeamento de colunas** — `engine._auto_map_column` casa `id/title/abstract/manual_tags` por nome exato → case-insensitive → sem acentos → aliases conhecidos.
3. **Preparação da config** — o controller carrega config + termos, monta o `NormalizationEngine` e pré-compila os padrões de cada bloco (e T0). Ver [[Arquitetura - Camada App e Controller]].
4. **Triagem** — `process_articles` roda o [[Algoritmo - Pipeline de Triagem|pipeline]] por artigo.
5. **Saída** — DataFrame com colunas por bloco (`RawScore_`, `FinalScore_`, `BestLevel_`, `Status_`, `Highlights_`, `AntiHighlights_`, `Flags_`), mais `Final_Decision`, `Decision_Reason`, e dados do T0.
6. **Exportação** — XLSX, relatório `.txt`, relatório acadêmico `.md`, e o ZIP com `protocol.json`. Ver [[Reprodutibilidade e Pacote Acadêmico]].

## Comandos de apoio ao fluxo

| Comando | Quando usar |
|---|---|
| `doctor` | **Antes** de rodar: confere arquivos, colunas detectadas, termos válidos |
| `preview` | Roda em amostra para calibração rápida |
| `coverage` | Identifica dead/broad terms na calibração |
| `run` | Triagem completa |
| `diff` | Compara duas execuções (o que mudou) |
| `export` | Regenera o pacote acadêmico a partir de um resultado |

---

Relacionado: [[Arquitetura - Visão Geral]] · [[Algoritmo - Pipeline de Triagem]] · [[Reprodutibilidade e Pacote Acadêmico]] · [[Home]]
