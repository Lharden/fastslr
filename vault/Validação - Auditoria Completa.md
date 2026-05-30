---
tags: [fastslr, validacao, auditoria]
---

# 🔬 Validação - Auditoria Completa

Auditoria completa do FastSLR com verificação em runtime de cada achado. Foram **confirmados 46 findings** (todos reproduzidos empiricamente ou por leitura direta de código), distribuídos em: **0 críticos** (todos os candidatos a crítico foram rebaixados após verificação de alcançabilidade/impacto), **15 de severidade alta**, **17 de severidade média** e **14 de severidade baixa**. Além disso, **24 findings foram refutados** (falso-positivos por inalcançabilidade em uso normal, dead code, comportamento documentado/intencional ou premissa factual incorreta) e ficam registrados na seção própria para evitar re-investigação. Nenhum dos findings confirmados causa perda de dados ou corrupção silenciosa de decisões de triagem no fluxo padrão; os de maior gravidade concentram-se em (1) lógica de matching de termos técnicos com símbolos (C++, C#, .NET), (2) robustez de I/O e encoding, e (3) consistência de UX/tratamento de erros na CLI. Tema transversal recorrente: **cobertura de teste ausente** — quase todos os achados têm `covered_by_test: false`.

## Resumo por severidade

| Severidade | Contagem |
|------------|----------|
| 🔴 Crítica | 0 |
| 🟠 Alta    | 15 |
| 🟡 Média   | 17 |
| 🟢 Baixa   | 14 |
| **Total confirmado** | **46** |

> [!note] Nota sobre severidades
> Todos os findings originalmente classificados como "crítica" foram **rebaixados para alta** após verificação: o impacto real é falso-positivo de triagem (artigo marcado errado, mas FLAGGED iria a revisão humana), degradação de qualidade de normalização, ou escrita/exclusão de arquivo auto-infligida via CLI local — nenhum com perda de dados, corrupção silenciosa de decisão ou superfície de rede. As severidades abaixo refletem o `severity_adjusted` verificado.

---

## 🟠 Severidade Alta

### special-rule-single-flagged-block-vacuous-approve — Regra especial aprova bloco único FLAGGED (all() vacuamente True)

> [!bug] APPROVED_FINAL indevido para bloco único na fronteira
> Um artigo cuja única dimensão está apenas na fronteira de score é marcado APROVADO em vez de FLAGGED.

- **Severidade**: Alta (rebaixada de crítica — impacto é falso-positivo de triagem, sem perda de dados; FLAGGED iria a revisão humana)
- **Categoria**: bug-logica
- **Local**: `src/fastslr/core/scoring.py:447-461` (make_final_decision, passo 4)
- **Descrição**: Com 1 único bloco FLAGGED-por-score, a condição `len(score_flagged)==1` é True e `len(approved_blocks)==total_blocks-1 == 0` também (0==0). Em seguida `all(s >= threshold for s in approved_scores)` com `approved_scores=[]` é **vacuamente True**, resultando em APPROVED_FINAL com razão "Special rule: 0 approved". Contradiz a intenção documentada em [[Algoritmo - Decisão Final]] (compensar bloco-fronteira com OUTROS blocos fortes — sem outros blocos não há compensação).
- **Repro**: `make_final_decision({'A': BlockEvaluation(status='FLAGGED', final_score=10.0)}, None, gp)` com `enable_special_approval_rule=True`, `decision_policy='special'` → `('APPROVED_FINAL','Special rule: 0 approved (scores >= 40.0)')`. Com a regra desabilitada o mesmo input retorna FLAGGED_FINAL.
- **Fix sugerido**: Adicionar guarda `and len(approved_blocks) >= 1` na condição (linhas 451-455), OU guardar `approved_scores and all(...)` na linha 457 para evitar a verdade vacua sobre lista vazia.
- **Coberto por teste**: Não (nenhum teste exercita a regra especial; conftest/test_compliance só setam a flag em fixtures).

### word-boundary-nonword-suffix-fails — `\b` após termo terminando em não-word-char nunca casa (C++ perde matches)

> [!bug] Perda silenciosa total de termos técnicos comuns
> C++, C#, .NET e F# nunca casam no caminho default (is_regex=False).

- **Severidade**: Alta
- **Categoria**: bug-logica
- **Local**: `src/fastslr/core/patterns.py:35`
- **Descrição**: O padrão envolve o termo em `\b...\b`. Quando o termo começa/termina em caractere não-word após `re.escape`, o `\b` exige transição word↔nonword impossível. `'C++'` compila como `\bC\+\+\b` que NUNCA casa ('C++ language', 'I like C++.', 'C++' isolado → todos None). Para `.NET` → `\b\.NET\b`: 'the .NET framework' → None, mas 'X.NET' casa (boundary errado). Ver [[Algoritmo - Padrões e Proximidade]].
- **Repro**: `re.compile(r'\bC\+\+\b', re.I).search('C++ language')` → None ; `re.compile(r'\b\.NET\b', re.I).search('the .NET framework')` → None mas `.search('X.NET')` → match `.NET`.
- **Fix sugerido**: Substituir `\b` fixos por boundaries condicionais ao tipo do char da borda: prefixar `(?<!\w)` só se `term[0]` é word-char, sufixar `(?!\w)` só se `term[-1]` é word-char; quando a borda é não-word, relaxar o boundary daquele lado. Adicionar testes para C++, C#, .NET, F#.
- **Coberto por teste**: Não (test_word_boundary só testa 'oil', palavra limpa).

### symbol-wordboundary-broken — Heurística `\b` para symbol_replacement com letra quebra c++, c#, .net

> [!bug] Regras de symbol_replacement silenciosamente inertes
> O caso de uso central (c#, c++, .net, f#) é silenciosamente inerte ou casa o alvo errado.

- **Severidade**: Alta (rebaixada de crítica — degradação de normalização, não corrupção de dados; símbolos puros funcionam)
- **Categoria**: bug-logica
- **Local**: `src/fastslr/core/normalization.py:71-73`
- **Descrição**: Para símbolos com letra (`re.search(r'[A-Za-z]', symbol)`) usa-se `rf'\b{re.escape(symbol)}\b'`. Como `+ # & .` não são `\w`, o `\b` ancora errado: `'c++'` → `\bc\+\+\b` não casa 'c++' isolado mas casa 'c++x'; `'c#'` → `\bc\#\b` nunca casa; `'.net'` → `\b\.net\b` não casa '.net' isolado mas casa 'a.net'. Ver [[Algoritmo - Normalização]].
- **Repro**: `NormalizationEngine({'enabled':True,'symbol_replacements':{'c#':'csharp'}})` → `normalize('using C# today')` → 'using c# today' (c# nunca substituído).
- **Fix sugerido**: Não usar `\b` cego; aplicar lookahead/lookbehind condicional por extremidade (`(?<!\w)` só quando a borda for `\w`; ou limites baseados em whitespace/início-fim). Adicionar testes para c++, c#, .net, f#, r&d.
- **Coberto por teste**: Parcial — só o símbolo '&' (branch else `str.replace`, que funciona); branch `re.sub/\b` tem cobertura zero.

### detect-encoding-chardet-ausente-cp1252 — Sem chardet, _detect_encoding cai para utf-8 e arquivos cp1252/Latin-1 falham com erro opaco

> [!bug] Falha de carga de exports europeus com erro que mascara a causa
> Exports Scopus/WoS/Excel-CSV em Windows-1252/Latin-1 falham com "Unable to load delimited table" sem mencionar encoding.

- **Severidade**: Alta
- **Categoria**: robustez
- **Local**: `src/fastslr/core/io.py:99-104` (_detect_encoding) + `141-152` (_load_delimited_table)
- **Descrição**: chardet é import opcional (não instalado por default — é extra `[chardet]`). Sem ele `_detect_encoding` retorna sempre 'utf-8'. Um CSV cp1252 'Café;Über' lança UnicodeDecodeError (byte 0xe9); `_load_delimited_table` captura `except Exception` por separador e continua, então TODOS falham e o usuário recebe só "Unable to load delimited table: {path}" sem mencionar encoding. Ver [[Fluxo de Dados]].
- **Repro**: Salvar CSV em cp1252 com acentos; sem chardet, `load_table_safe` falha com mensagem opaca. O arquivo carrega com `encoding='cp1252'`.
- **Fix sugerido**: Tentar lista de fallback (utf-8-sig, utf-8, cp1252, latin-1) quando chardet ausente; `latin-1` nunca falha na decodificação e garante carga em último recurso. Mensagem de erro deve mencionar encoding. Considerar chardet obrigatório.
- **Coberto por teste**: Não (todos os fixtures escrevem utf-8).

### profiles-path-traversal — Nome de perfil sem sanitização permite path traversal em save/load/delete

> [!bug] Escrita/exclusão arbitrária de arquivo fora do sandbox
> `'../../../evil'` resolve para `C:\Users\evil.json`, escapando totalmente `~/.fastslr/profiles`.

- **Severidade**: Alta (rebaixada de crítica — vetor auto-infligido via CLI local, sem superfície de rede/multiusuário)
- **Categoria**: robustez
- **Local**: `src/fastslr/app/profiles.py:34, 55, 95`
- **Descrição**: `safe_name = name.replace(' ', '_').lower()` + `profiles_dir / f'{safe_name}.json'` NÃO remove separadores nem `..`. `save_profile` escreve JSON arbitrário fora do sandbox; `delete_profile` pode `unlink()` arquivo arbitrário. O nome vem de `typer.Argument` (CLI) e de `_profile_name` em profile.json (possível fonte maliciosa compartilhada).
- **Repro**: `profiles.save_profile('../../../evil', {})` → grava em `C:\Users\evil.json`. `delete_profile('../../../evil')` removeria o mesmo.
- **Fix sugerido**: `safe_name = re.sub(r'[^a-z0-9_-]+', '_', name.strip().lower())`, rejeitar vazio, e validar `(profiles_dir / f'{safe_name}.json').resolve().is_relative_to(profiles_dir.resolve())` nas três funções. `list_profiles` já usa `glob('*.json')`, não afetado.
- **Coberto por teste**: Não (zero referências a save/load/delete_profile em tests/).

### package-data-nao-incluido-no-build — locales/*.json e default_config.json não serão empacotados no pip install

> [!bug] UI inteira exibe chaves cruas após pip install
> Sem os locales no wheel, `_load_locale_file` loga "Locale file not found" e `_()` cai no fallback do próprio key.

- **Severidade**: Alta (rebaixada de crítica — degrada graciosamente via fallback, sem crash)
- **Categoria**: config-setup
- **Local**: `pyproject.toml:32-33`
- **Descrição**: Build usa `setuptools.build_meta` com apenas `packages.find where=['src']`, sem `include-package-data`, `package-data` nem MANIFEST.in. Por default o wheel inclui SÓ `.py`. `src/fastslr/i18n/locales/{en,pt_BR,es}.json` somem (SOURCES.txt do egg-info confirma a exclusão). Após `pip install`, a UI exibe chaves como 'project_config_hint' em vez de texto traduzido. **Correções ao finding original**: (1) `py.typed` ESTÁ no wheel (SOURCES.txt:6) — afirmação de perda de tipos é falsa; (2) `default_config.json` não é carregado em runtime de produção (só fixture/template).
- **Repro**: `python -m build`; instalar o wheel em venv limpo; `python -m zipfile -l dist/fastslr-3.0.0-*.whl` não mostra `locales/*.json`. Rodar qualquer comando → strings de UI como chaves.
- **Fix sugerido**: Adicionar `[tool.setuptools.package-data] fastslr = ['py.typed','i18n/locales/*.json','core/*.json']` (ou `include-package-data=true` + MANIFEST.in). Migrar `i18n/__init__.py` para `importlib.resources.files('fastslr.i18n')`.
- **Coberto por teste**: Não (nenhum teste cobre packaging).

### run-aborts-on-spurious-warnings-noninteractive — run aborta (exit 1, zero saída) não-interativo por 34 avisos falsos de normalização

> [!bug] Bloqueador de workflow em CI/pipe disfarçado de aviso
> O usuário segue o comando que o `doctor` sugeriu e o run não roda — exit 1, diretório de saída vazio.

- **Severidade**: Alta
- **Categoria**: ux-erro-usuario
- **Local**: `src/fastslr/app/cli.py:209-215` (typer.confirm 'continue_with_warnings'); avisos em `src/fastslr/core/config.py:208-211`
- **Descrição**: As 34 linhas GLOBAL de normalização do `terms_final.csv` (kind vazio por design) geram avisos "Row N: empty kind. Row skipped." — **falsos**, pois as regras SÃO usadas (extraídas em config.py:183 antes do loop). Com warnings, `run` pede `[y/N]` default=False; sem TTY (pipe/CI/stdin fechado) cai no default N → ABORTA com exit 1, zero saída. Ver [[Algoritmo - Pipeline de Triagem]].
- **Repro**: `python -m fastslr run data/Final_Corpus.csv -c .../default_config.json -t data/terms_final.csv -o /tmp/out < /dev/null` → 34 avisos + "Aborted." + exit 1. Workaround: `--quiet` → exit 0 e gera os 6 arquivos.
- **Fix sugerido**: Não emitir o aviso quando `normalization_type` está preenchido (são regras, não termos). Quando `sys.stdin.isatty()` falso ou `--quiet`, prosseguir por padrão ou exigir flag explícita `--yes`/`--no-confirm`.
- **Coberto por teste**: Não.

### flagging-threshold-default-zero-flags-zero-score — `flagging_thresholds.get(best_level, 0)` faz score 0.0 ser FLAGGED em vez de REJECTED

- **Severidade**: Alta (nota: triagem interna rebaixou para média — só dispara com nível fora do range)
- **Categoria**: bug-logica
- **Local**: `src/fastslr/core/scoring.py:292,297` (evaluate_block)
- **Descrição**: `flagging_threshold` usa default 0; a comparação é `final_score >= flagging_threshold`. Com `final_score == 0.0` (nível fora de level_scores, ou nível com 0 pontos), `0.0 >= 0` é True → FLAGGED. Um match positivo com evidência de score ZERO deveria ser REJECTED, não poluir a fila de revisão. Ver [[Algoritmo - Avaliação de Bloco]].
- **Repro**: Bloco com termo nível 6 (fora de level_scores) → best_level=6, raw_score=0, `flagging_thresholds.get(6,0)=0` → `0.0>=0` → FLAGGED 'Score 0.00 >= flag threshold 0 (L6)'.
- **Fix sugerido**: Exigir `final_score > 0 and final_score >= flagging_threshold`, OU default None e sinalizar só quando threshold existir e final_score > 0. Validar que todo best_level possível tem entrada em flagging_thresholds.
- **Coberto por teste**: Não.

### flagging-threshold-l4-divergence / flagging-threshold-divergence-constants-vs-presets / thresholds-flag-divergentes-3-fontes — Threshold de flagging nível 4 inconsistente: constants.py=8 vs presets/JSON=7

> [!note] Três findings sobre a mesma divergência (consolidados)
> `flagging-threshold-l4-divergence`, `flagging-threshold-divergence-constants-vs-presets` e `thresholds-flag-divergentes-3-fontes` descrevem o mesmo defeito. Já registrado como bug #1 em [[Validação - Bugs e Riscos Conhecidos]].

- **Severidade**: Alta (categoria config/reprodutibilidade; nota: triagem rebaixou impacto prático para média — caminho off-nominal estreito)
- **Categoria**: config-setup / reprodutibilidade
- **Local**: `src/fastslr/core/constants.py:47` (DEFAULT_FLAGGING_THRESHOLDS L4=8) vs `src/fastslr/core/presets.py:25` (standard L4=7) vs `src/fastslr/core/default_config.json:36` (LIMITES_SINALIZADO["4"]=7)
- **Descrição**: As três fontes de verdade divergem APENAS no nível 4 (8 vs 7). `load_global_params` (config.py:96-101) usa DEFAULT_FLAGGING_THRESHOLDS só como fallback quando LIMITES_SINALIZADO ausente. Artigo com best_level=4 e final_score em [7.0, 8.0) é FLAGGED com preset/JSON mas REJECTED com fallback de constants → triagem não-determinística conforme caminho de config. Ver [[Algoritmo - Pontuação (Scoring)]].
- **Repro**: `print(DEFAULT_FLAGGING_THRESHOLDS[4], LEVEL_PRESETS['standard']['flagging_thresholds'][4], json['global']['LIMITES_SINALIZADO']['4'])` → `8 7 7`.
- **Fix sugerido**: Fonte única de verdade: alterar `constants.py:47` para `{...,4:7,...}` (alinhar ao caminho de produção), ou derivar presets/JSON de constants. Adicionar teste que afirme igualdade entre as três fontes. **Corrigir `conftest.py:24` que ainda hardcoda 4:8.**
- **Coberto por teste**: Não (pior: conftest.py:24 perpetua o valor divergente).

### out-of-range-level-flagged-zero-score — Termo positivo com level fora do range vira FLAGGED com score 0

- **Severidade**: Alta (nota: triagem rebaixou para média — só com erro de digitação de nível)
- **Categoria**: bug-logica
- **Local**: `src/fastslr/core/config.py:243-249` (só avisa, não zera o level) + `src/fastslr/core/patterns.py:142-148` + `src/fastslr/core/scoring.py:290-301`
- **Descrição**: Quando um termo 'pos' tem level numérico válido porém FORA dos níveis configurados (ex.: 7 com PONTUACAO_NIVEIS 1-5), `parse_terms_csv` só emite warning "Score contribution will be 0" mas MANTÉM level='7'. No scoring vira best_level=7, score 0, `flagging_thresholds.get(7,0)=0` → `0.0>=0` → FLAGGED. A mensagem é enganosa: o termo não fica inerte, empurra o artigo para revisão indevida.
- **Repro**: CSV `'CTX,pos,quantum,7,any,0'` com PONTUACAO_NIVEIS 1-5; evaluate_block sobre 'quantum' → best_level=7, final_score=0.0, status=FLAGGED.
- **Fix sugerido**: No ramo 'level_int not in configured_levels' (config.py:243), além do warning, fazer `level=''` (espelhando a linha 262). Adicionar teste cobrindo level fora do range.
- **Coberto por teste**: Não.

### proximity-negative-gap-literal-no-match — max_gap negativo gera `{0,-1}` tratado como literal → proximidade nunca casa (silencioso)

- **Severidade**: Alta (nota: triagem rebaixou para média — exige misconfiguração de knob não-default)
- **Categoria**: robustez
- **Local**: `src/fastslr/core/patterns.py:60`; `src/fastslr/core/config.py:132`
- **Descrição**: O gap é `'(?:\s+{token_unit}){{0,{max_gap}}}\s+'`. Com `max_gap=-1` resulta `'(?:\s+\S+){0,-1}\s+'`. Python NÃO levanta `re.error` para `{0,-1}` — trata como TEXTO LITERAL, então nenhum documento casa e o try/except não dispara. `max_gap` vem de `int(global_cfg.get('MAX_GAP_BETWEEN_TERMS', 2))` sem validação de limite inferior. Ver [[Algoritmo - Padrões e Proximidade]].
- **Repro**: `compile_proximity_pattern('machine','learning', max_gap=-1)` retorna Pattern válido cujo `.search('machine of learning')` → None.
- **Fix sugerido**: Validar `max_gap >= 0` em compile_proximity_pattern (clamp para 0 ou retornar None com warning) e em config.py (`max(0, int(...))`). Emitir warning quando o valor configurado for inválido.
- **Coberto por teste**: Não (só max_gap positivo).

### symbol-pass-after-lowercase-uppercase-key-dead — Chave de símbolo com letra maiúscula nunca casa (pass roda após lower())

- **Severidade**: Alta (nota: triagem rebaixou para média — no-op silencioso, opt-in)
- **Categoria**: bug-logica
- **Local**: `src/fastslr/core/normalization.py:26,69-75`
- **Descrição**: `_symbols` guarda as chaves CRUAS (linha 26, sem `lower()`). O texto é lowercased na linha 69 ANTES do loop de símbolos (71-75). Qualquer chave digitada com maiúscula ('C#', '.NET', 'C++') jamais casa o texto já minúsculo. Combinado com o bug do `\b`, regras de símbolo são extremamente frágeis. Ver [[Algoritmo - Normalização]].
- **Repro**: `extract_normalization_rules` com term='C#' guarda chave 'C#'; `normalize('C# rocks')` → 'c# rocks' (chave C# não casa).
- **Fix sugerido**: Lowercasear chaves de symbol_replacements na construção (espelhando abbreviations/compounds linhas 169/171) E corrigir o `\b` para chaves com símbolos nas pontas. Idealmente `re.IGNORECASE`.
- **Coberto por teste**: Não (só '&', branch else).

### highlight-term-quote-breaks-coverage-parse — Termo com aspas duplas quebra _HIGHLIGHT_TERM_RE e gera falso dead-term

- **Severidade**: Alta (nota: triagem rebaixou para média — confinado ao relatório de cobertura advisory)
- **Categoria**: bug-logica
- **Local**: `src/fastslr/core/coverage.py:25` (_HIGHLIGHT_TERM_RE) + `src/fastslr/core/io.py:316` (pack_highlights)
- **Descrição**: `pack_highlights` serializa `term="{m.term}"` sem escapar aspas. Termo com `"` embutido (ex.: medição de "qualidade") quebra a regex `term="([^"]+)"\s+sec=(\w+)` (findall → []). O hit não é contabilizado, o termo nunca entra em matched_terms e — estando em all_configured_terms — `analyze_term_coverage` o classifica como dead-term e sugere "remover". Afeta também section_distribution e broad-terms.
- **Repro**: `_HIGHLIGHT_TERM_RE.findall('term="machine "learning"" sec=title L=1 row=0 type=exact')` → [].
- **Fix sugerido**: Serializar com `json.dumps(m.term)` ou delimitador estruturado por match; ou regex não-gananciosa ancorada por `' sec='`. Validar contra aspas/espaços/pipe.
- **Coberto por teste**: Não.

### preview-coverage-terms-raw-traceback-missing-files — preview/coverage/terms vazam FileNotFoundError cru quando arquivos não existem

- **Severidade**: Alta (nota: triagem rebaixou para média — UX, exit code já correto)
- **Categoria**: ux-erro-usuario
- **Local**: `src/fastslr/app/cli.py:242-288, 392-433`; `controller.py:400-417, 422-437, 631-694`
- **Descrição**: Diferente de run()/export() (que checam .exists() + mensagem amigável + Exit(1)), preview valida só input_file; coverage e terms não validam nada. O controller chama load_config/load_table_safe que levantam FileNotFoundError; sem callback/except global no Typer, o usuário recebe traceback Python cru. A chave i18n `config_not_found` já existe e é usada em run. Ver [[Arquitetura - Camada App e Controller]].
- **Repro**: `fastslr terms -c nao_existe.json` → traceback cru de FileNotFoundError.
- **Fix sugerido**: Adicionar checagem .exists() com `t('config_not_found'/'file_not_found')` + Exit(1), OU centralizar via decorator/callback que captura FileNotFoundError/ValueError do controller.
- **Coberto por teste**: Não.

### diff-outer-merge-nan-not-missing — diff marca artigos exclusivos como 'nan' em vez de 'MISSING'

- **Severidade**: Alta (nota: triagem rebaixou para média — label confuso, sem corrupção)
- **Categoria**: bug-logica
- **Local**: `src/fastslr/app/controller.py:474-484` (diff_results)
- **Descrição**: O merge outer cria NaN para IDs em apenas um arquivo. `str(row.get('Final_Decision_a', 'MISSING'))` nunca usa o default 'MISSING' porque a coluna sempre existe após o merge — `row.get` retorna o NaN e `str(NaN)` vira 'nan'. O usuário vê 'REJECTED -> nan' e 'nan -> APPROVED'.
- **Repro**: result_a com IDs {1,2,3}, result_b com {1,2,4} → linhas com 'nan' nas colunas de decisão.
- **Fix sugerido**: `old = 'MISSING' if pd.isna(row['Final_Decision_a']) else str(row['Final_Decision_a'])` (idem _b), ou `merged.fillna('MISSING')` após o merge.
- **Coberto por teste**: Não (teste só cobre IDs presentes em ambos).

### diff-id-fallback-keyerror — diff quebra com KeyError cru quando arquivos não compartilham coluna de ID

> [!bug] Crash não tratado em diff de arquivos heterogêneos
> A=[ArtID,Final_Decision] vs B=[DOI,Final_Decision] → KeyError "['ArtID'] not in index".

- **Severidade**: Alta (nota: triagem rebaixou para média — crash contido, sem perda de dados)
- **Categoria**: crash-runtime
- **Local**: `src/fastslr/app/controller.py:455-472` (diff_results)
- **Descrição**: Quando nenhum candidato (ID/id/Key/key) existe em AMBOS, o fallback é `id_col = df_a.columns[0]`. Se essa coluna não existir em B, `df_b[[id_col, 'Final_Decision']]` e `pd.merge(on=id_col)` levantam KeyError cru. Sem except global na CLI, vira traceback.
- **Repro**: `fastslr diff result_a.csv result_b.csv` com colunas de ID divergentes → KeyError cru.
- **Fix sugerido**: Validar que id_col existe em ambos antes do merge; senão, levantar ValueError amigável ("Nenhuma coluna de ID comum: A tem X, B tem Y") e tratar na CLI com Exit(1).
- **Coberto por teste**: Não (teste só cobre caminho feliz com ID compartilhado).

### create-project-silent-overwrite — new-project sobrescreve projeto existente sem confirmação

- **Severidade**: Alta (nota: triagem rebaixou para média — scaffolding recuperável, exige re-invocar comando)
- **Categoria**: ux-erro-usuario
- **Local**: `src/fastslr/app/controller.py:499-572` (create_project); `cli.py:325-364`
- **Descrição**: `create_project` faz `mkdir(exist_ok=True)` e escreve config.json/terms.xlsx/terms.csv sem checar existência. Rodar `new-project` duas vezes sobrescreve silenciosamente os arquivos com os templates, perdendo edições do usuário. A CLI ainda imprime "Projeto criado". Já documentado como #12 em [[Validação - Bugs e Riscos Conhecidos]].
- **Repro**: `fastslr new-project rev --blocks CTX,TECH`; editar terms.xlsx; repetir → edições perdidas.
- **Fix sugerido**: Detectar se output_dir já contém config.json/terms.xlsx e abortar com erro amigável ou exigir `typer.confirm`/flag `--force`.
- **Coberto por teste**: Não.

### no-global-exception-handler — CLI sem handler global: qualquer erro do controller vira traceback cru

- **Severidade**: Alta (nota: triagem rebaixou para média — UX + vazamento de paths internos, exit 1 já correto)
- **Categoria**: ux-erro-usuario
- **Local**: `src/fastslr/app/cli.py:30-35, 512-513`; `src/fastslr/__main__.py:5`
- **Descrição**: Causa-raiz transversal. O app Typer não tem callback raiz nem wrapper try/except. Comandos com pré-validação (run, export, profile-load) escapam, mas preview/coverage/terms/diff/new-project/profile-save propagam exceções como traceback. Ex.: `new-project --preset typo` → ValueError cru; `profile save -c nao_existe.json` → FileNotFoundError cru.
- **Repro**: `python -m fastslr profile save p -c nao_existe.json` → traceback com paths internos + exit 1.
- **Fix sugerido**: Wrapper `main()` chamando `app()` dentro de try/except FileNotFoundError/ValueError/JSONDecodeError + sys.exit(1), OU `result_callback`/except_hook do Typer. Padronizar para que nenhum comando exponha traceback por erro de input previsível.
- **Coberto por teste**: Não (nenhum teste de CLI no projeto).

---

## 🟡 Severidade Média

### proximity-requires-adjacent-space — Proximidade exige sempre ≥1 espaço; 'machine-learning'/'input/output' não casam

- **Severidade**: Média
- **Categoria**: bug-logica
- **Local**: `src/fastslr/core/patterns.py:60`
- **Descrição**: O gap termina sempre com `\s+` obrigatório. Separadores não-espaço (hífen, barra, vírgula colada) não casam: 'machine-learning', 'machine/learning', 'machine,learning' → None. Em SLR é comum compostos hifenizados/com barra → falso-negativo silencioso (perda de recall). Formas com espaço (and/or/barra-espaçada) funcionam. Ver [[Algoritmo - Padrões e Proximidade]].
- **Repro**: `compile_proximity_pattern('machine','learning',max_gap=0).search('machine-learning')` → None.
- **Fix sugerido**: Generalizar o separador para `[\s\-/.,]+` quando max_gap permite tokens intermediários; decidir explicitamente se proximidade aceita hifenizados. Testes para 'machine-learning', 'input/output'.
- **Coberto por teste**: Não.

### compound-splits-only-first-separator — detect_compound_terms divide só no primeiro separador

- **Severidade**: Média
- **Categoria**: bug-logica
- **Local**: `src/fastslr/core/patterns.py:71-89`
- **Descrição**: `_COMPOUND_RE` usa `(.+?)` e `(.+)` capturando só o primeiro split. 'A and B and C' → `[('A','B and C')]`. O part_b vira termo único via `re.escape`, gerando padrão que exige a string literal 'B and C' adjacente — quase nunca casa. Para compostos de 3+ partes a proximidade fica quebrada silenciosamente.
- **Repro**: `detect_compound_terms('A and B and C')` → `[('A','B and C')]`; `detect_compound_terms('A/B/C')` → `[('A','B/C')]`.
- **Fix sugerido**: Dividir recursivamente em TODOS os separadores (`re.split` com alternância and|&|or|/) e gerar pares de proximidade. Definir semântica (todos-os-pares vs sequencial) e testar 3+ componentes.
- **Coberto por teste**: Não (só 2 partes).

### silent-mismatch-term-vs-article — Termo e texto podem normalizar diferente (mismatch silencioso)

- **Severidade**: Média (rebaixada de crítica — só alcançável via regra de símbolo mal-formada pelo usuário)
- **Categoria**: bug-logica
- **Local**: `src/fastslr/core/normalization.py:31-80` (consumido em patterns.py:108-114 e scoring.py:20-34)
- **Descrição**: Normalização de símbolo é contexto-dependente (`\b` depende dos vizinhos). Termo isolado e ocorrência no texto podem normalizar divergente → busca falha sem aviso. Regra `'.net'→'dotnet'`: termo '.net' fica '.net' mas 'asp.net' vira 'aspdotnet' → a regex de '.net' nunca encontra. Só alcançável com regra patológica (token alfanumérico via symbol_replacement); '&'→'and' funciona simetricamente. Ver [[Algoritmo - Normalização]].
- **Repro**: `symbol_replacements={'.net':'dotnet'}`: `normalize('.net')='.net'`; `normalize('asp.net and vb.net')='aspdotnet and vbdotnet'`.
- **Fix sugerido**: Garantir normalização determinística e contexto-independente (ver fixes de `\b`). Adicionar diagnóstico: se normalize(term) ainda contém char que uma regra deveria eliminar, emitir warning. Idealmente round-trip: `normalize(term) in normalize(texto)`.
- **Coberto por teste**: Não (só '&').

### rule-order-dependent-output — Ordem das linhas no CSV altera resultado da normalização (símbolos sobrepostos)

- **Severidade**: Média
- **Categoria**: robustez
- **Local**: `src/fastslr/core/normalization.py:71-78`
- **Descrição**: O loop de símbolos itera na ordem de inserção do dict (= ordem das linhas do CSV). Símbolos sobrepostos produzem saídas diferentes conforme a ordem → reprodutibilidade fraca. Exige uma chave ser substring de outra (config incomum). Ver [[Algoritmo - Normalização]] e [[Reprodutibilidade e Pacote Acadêmico]].
- **Repro**: linhas `['&','r&d']` vs `['r&d','&']` produzem saídas diferentes para 'r&d lab'.
- **Fix sugerido**: Ordenar regras por comprimento decrescente da chave (mais específica primeiro), ou regex alternada com prioridade explícita. Documentar precedência inter-classes (abbr→lower→símbolo→composto).
- **Coberto por teste**: Não.

### run-config-validation-before-terms-exists-traceback — run() chama _prepare_config antes de validar terms, vazando erros crus

- **Severidade**: Média
- **Categoria**: ux-erro-usuario
- **Local**: `src/fastslr/app/cli.py:199-206`; `controller.py:204-233` (_prepare_config)
- **Descrição**: Após checar input/config, run() chama `_prepare_config` que faz load_config (pode levantar JSONDecodeError), parse_terms_csv (ValueError/FileNotFoundError) e precompile_patterns. Nenhuma é capturada → traceback. `doctor`/inspect_run_setup encapsula tudo e converte em erros amigáveis, mas run() não reaproveita → inconsistência de UX.
- **Repro**: config.json inválido OU terms.xlsx sem coluna 'term' → JSONDecodeError/ValueError cru, enquanto `doctor` mostra erro amigável.
- **Fix sugerido**: Envolver a preparação em try/except convertendo em mensagem amigável + Exit(1), ou reutilizar inspect_run_setup como gate inicial. Aplica também a preview/export/terms.
- **Coberto por teste**: Não.

### diff-no-friendly-error-for-valueerror — diff levanta ValueError cru quando falta coluna Final_Decision

- **Severidade**: Média
- **Categoria**: ux-erro-usuario
- **Local**: `src/fastslr/app/cli.py:291-301` (diff); `controller.py:449-452` (diff_results)
- **Descrição**: `diff_results` levanta `ValueError('File A is missing Final_Decision column')`. O comando diff não envolve em try/except nem checa .exists(). Mensagem técnica em inglês, inconsistente com a UX i18n PT-BR.
- **Repro**: `fastslr diff sem_decisao.csv outro.csv` → ValueError cru; `fastslr diff nao_existe.csv b.csv` → FileNotFoundError cru.
- **Fix sugerido**: Checar existência de result_a/result_b com `t('file_not_found')` + Exit(1), e envolver diff_results em try/except; i18n da mensagem de coluna ausente.
- **Coberto por teste**: Não.

### tui-worker-ui-access-from-thread — _run_triage acessa widgets via query_one fora do thread da UI

- **Severidade**: Média
- **Categoria**: robustez
- **Local**: `src/fastslr/app/tui.py:235-243`
- **Descrição**: `_run_triage` é `@work(thread=True)`. As escritas usam `call_from_thread` corretamente, mas as leituras iniciais `self.query_one(...).value` (237-243) rodam direto no thread do worker. A doc do Textual exige `call_from_thread` para funções não-thread-safe (query_one percorre o DOM). Janela de corrida estreita mas viola o contrato documentado.
- **Repro**: Inspeção: linhas 237-243 chamam query_one no worker sem call_from_thread.
- **Fix sugerido**: Ler os 4 inputs em `start_triage` (thread da UI) e passá-los como argumentos para `_run_triage(self, input_path, config_path, terms_path, output_dir)`.
- **Coberto por teste**: Não (TUI sem cobertura).

### chardet-opcional-muda-resultado — Detecção de encoding não-determinística entre ambientes (depende do extra 'chardet')

- **Severidade**: Média
- **Categoria**: reprodutibilidade
- **Local**: `src/fastslr/core/io.py:99-104`
- **Descrição**: `_detect_encoding` usa chardet quando disponível, senão utf-8. chardet é optional-dependency. O MESMO arquivo pode ser lido com encodings diferentes conforme o usuário tenha ou não `fastslr[chardet]`. **Correção ao finding**: o campo config `encoding` só é usado na EXPORTAÇÃO (io.py:216), nunca na leitura de entrada; e o modo de falha dominante para cp1252 é falha dura (ValueError), não mojibake. Ver [[Reprodutibilidade e Pacote Acadêmico]].
- **Repro**: CSV cp1252 com acentos: run sem chardet (falha/utf-8) vs com chardet (detecta cp1252) → resultados divergem.
- **Fix sugerido**: Cadeia de encodings determinística na leitura (utf-8-sig → cp1252/latin-1) independente de chardet, consultando `config.encoding` quando definido; ou promover chardet a obrigatório. Adicionar regressão cp1252.
- **Coberto por teste**: Não.

### stats-inconsistent-denominator-error-rows — collect_statistics mistura denominadores (error rows em decision_distribution mas não em block_performance/score_distribution)

- **Severidade**: Média (nota: triagem rebaixou para baixa — error_count já exposto; só rotulagem)
- **Categoria**: reprodutibilidade
- **Local**: `src/fastslr/core/engine.py:124-153` (collect_statistics) + `319-327` (row de erro)
- **Descrição**: Linhas de erro (ERROR_POLICY='flag') têm só id/Final_Decision/Reason/version/timestamp — sem Status_*/FinalScore_* (NaN). `decision_distribution` CONTA as linhas de erro; `block_performance` e `score_distribution` IGNORAM os NaN. avg_score é calculado sobre denominador diferente do total, sem indicação. Ver [[Algoritmo - Pipeline de Triagem]].
- **Repro**: 2 sucessos + 1 erro: total=3, decision_distribution conta 3, mas mean calculado sobre 2 valores.
- **Fix sugerido**: Documentar/registrar o denominador de cada métrica; contar linhas de erro como categoria 'ERROR' em block_performance ou preencher Status_*='ERROR' e relatar n_valid vs n_total.
- **Coberto por teste**: Não (teste só verifica len/Final_Decision/error_count).

### symbol-replacement-value-not-lowercased — Valor de substituição de símbolo preserva maiúscula após o lower() global

- **Severidade**: Média (nota: triagem rebaixou para baixa — gatilho estreito)
- **Categoria**: bug-logica
- **Local**: `src/fastslr/core/normalization.py:26,69-75`
- **Descrição**: Diferente de abbreviations/compounds (forçados a lower() no `__init__`), os valores de symbol_replacements ficam crus. Como o pass de símbolos roda APÓS `normalized.lower()` (linha 69), um valor com maiúscula injeta maiúsculas que nunca são re-lowercased → casing inconsistente.
- **Repro**: `symbol_replacements={'+':'Plus'}`: `normalize('c++')` → 'cPlusPlus'.
- **Fix sugerido**: Lowercasear valores de symbol_replacements na construção (linhas 26/173), ou re-aplicar `.lower()` no return (linha 80). Política única de casefolding.
- **Coberto por teste**: Não (só valor lowercase 'and').

### lru-cache-on-n — Cache LRU manual é O(n) por acesso (list.remove e pop(0))

- **Severidade**: Média (nota: triagem rebaixou para baixa — overhead <10% do trabalho total)
- **Categoria**: performance
- **Local**: `src/fastslr/core/normalization.py:28-29,37-49`
- **Descrição**: Cache hit faz `_cache_order.remove(key)` (O(n)) e eviction `pop(0)` (O(n) shift). Com maxsize=2000 e abstracts, reinventa o que `functools.lru_cache`/`OrderedDict.move_to_end` fazem em O(1). Benchmark: ~23x mais lento que OrderedDict no bookkeeping, mas é fração pequena do custo total.
- **Repro**: 20000 hits na chave mais antiga em cache cheio → ~0.84s vs ~0.03s com OrderedDict.
- **Fix sugerido**: `collections.OrderedDict` com `move_to_end()`/`popitem(last=False)`, ou `functools.lru_cache(maxsize=2000)` em `_normalize_uncached`. Elimina também o risco de dessincronia `_cache`/`_cache_order`.
- **Coberto por teste**: Não (teste só verifica corretude).

### dup-detection-symbol-case-asymmetry — Detecção de duplicata de symbol_replacement: chave crua + comparação lowercased

- **Severidade**: Média (nota: triagem rebaixou para baixa — só mensageria de validação)
- **Categoria**: ux-erro-usuario
- **Local**: `src/fastslr/core/normalization.py:157-173`
- **Descrição**: A chave de symbol_replacement é guardada CRUA (linha 173) enquanto abbreviation/compound usam `term.lower()`. (1) 'C#' e 'c#' coexistem sem warning de duplicata; (2) a comparação em 160 (`existing != norm_target.lower()`) compara valor cru 'Plus' contra 'plus' → warning de duplicata FALSO-POSITIVO mesmo para linhas idênticas.
- **Repro**: Duas linhas idênticas `term='+' target='Plus'` → warning espúrio "already mapped to 'Plus'. Overwriting with 'Plus'.".
- **Fix sugerido**: Usar `term.lower()` como chave e comparar ambos os lados na mesma forma (casefold), simetria com abbreviation/compound. Cuidado: a engine usa o símbolo cru no re.search — casefold da chave precisa ser consistente.
- **Coberto por teste**: Não.

### detect-format-threshold-2-falso-positivo — detect_format com threshold ≥2 classifica errado CSVs genéricos

- **Severidade**: Média (nota: triagem rebaixou para baixa — adapters.py é dead code não cabeado)
- **Categoria**: bug-logica
- **Local**: `src/fastslr/core/adapters.py:51-78` (detect_format / _FORMAT_SIGNATURES)
- **Descrição**: `detect_format` retorna formato com overlap ≥2. Assinaturas WoS curtas {UT,TI,AB,SO}: um CSV com {'TI','AB','custom1'} é classificado 'wos' e apply_mapping renomeia TI→title, AB→abstract incorretamente. **Importante**: adapters.py NÃO é importado em lugar nenhum (dead code); a ingestão real usa io.py `_header_score` + campos configurados. Não alcançável no fluxo atual.
- **Repro**: `normalize_import(pd.DataFrame(columns=['TI','AB','custom1']))` → mapeia como WoS.
- **Fix sugerido**: Exigir colunas-âncora por formato (WoS só com 'UT'; Scopus só com 'EID'); threshold proporcional ao tamanho da assinatura; desempate determinístico. Aplicar preventivamente antes de integrar o módulo.
- **Coberto por teste**: Não.

### export-raw-subset-astype-str-1.0-vs-1 — export_raw_subset casa IDs via astype(str) e perde linhas float (1.0) vs int (1) — e é dead code

- **Severidade**: Média (nota: triagem rebaixou para baixa — dead code, fluxo padrão dtype=str)
- **Categoria**: bug-logica
- **Local**: `src/fastslr/core/io.py:406-418`
- **Descrição**: Match por `.astype(str)` nos dois lados: '1.0' (float) vs '1' (int/str) não casa → subset vazio silencioso. Atenuante: `load_table_safe` sempre usa `dtype=str` e o engine constrói `article_id = str(id_value)`, então no fluxo padrão ambos são string. **export_raw_subset é DEAD CODE** (0 call sites), mas exportado em `__all__`.
- **Repro**: `export_raw_subset(original_df key int [1,2,3], result_df ID float [1.0,2.0], ...)` → subset vazio.
- **Fix sugerido**: Normalizar IDs (floats inteiros como int antes de str), ou remover a função morta. Se mantida, adicionar teste e documentar pré-condição dtype=str.
- **Coberto por teste**: Não.

### migrate-protocol-snapshot-incompleto — migrate não adiciona chaves obrigatórias ausentes nem valida versão de origem

- **Severidade**: Média (nota: triagem rebaixou para baixa — API pública sem call-site interno)
- **Categoria**: reprodutibilidade
- **Local**: `src/fastslr/core/io.py:520-532` (migrate) + `503-517` (validate)
- **Descrição**: `migrate_protocol_snapshot` só seta protocol_version/schema_id e injeta 'methodology'. Não valida versão de origem (migra qualquer coisa, inclusive já-2.1/futuro) nem preenche as 7 chaves raiz obrigatórias. Um snapshot mínimo migrado fica inválido por validate_protocol_snapshot mas se apresenta como '2.1' para consumidores que só olham a versão. Ver [[Reprodutibilidade e Pacote Acadêmico]].
- **Repro**: `migrate_protocol_snapshot({'protocol_version':'1.0','inputs':{}})` → protocol_version='2.1' mas validate retorna 7 erros de chaves ausentes.
- **Fix sugerido**: Gate por versão origem→destino, preencher defaults para chaves raiz ausentes, e chamar validate_protocol_snapshot ao final. Recusar versões desconhecidas/futuras.
- **Coberto por teste**: Não (só happy-path v2.0 completo).

### run-terms-missing-not-validated — run() valida input e config mas não valida existência do arquivo de terms

- **Severidade**: Média (nota: triagem rebaixou para baixa — UX, run aborta com segurança)
- **Categoria**: ux-erro-usuario
- **Local**: `src/fastslr/app/cli.py:191-200` (run); `controller.py:204-209`
- **Descrição**: run() checa input_file e config com mensagens amigáveis mas nunca terms.exists(). Com `-t` errado, `_prepare_config` → parse_terms_csv → load_table_safe levanta FileNotFoundError cru. `doctor` (inspect_run_setup) trata terms ausente amigavelmente — inconsistência.
- **Repro**: `fastslr run articles.csv -c config.json -t terms_errado.xlsx` → FileNotFoundError cru.
- **Fix sugerido**: `if terms is not None and not terms.exists(): console.print(t('file_not_found', path=terms)); raise typer.Exit(1)` em run/preview/coverage (mesma checagem do doctor).
- **Coberto por teste**: Não.

### preview-sample-zero-silent-empty — preview --sample 0 processa zero artigos ou crasha cru

- **Severidade**: Média (nota: triagem rebaixou para baixa — niche, input deliberado)
- **Categoria**: robustez
- **Local**: `src/fastslr/app/cli.py:247`; `controller.py:400-416`; `core/engine.py:356-363`
- **Descrição**: `--sample` sem validação de mínimo. `--sample 0`: `df.sample(n=0)` → DataFrame vazio, CLI imprime stats vazias + "0 artigos" como sucesso. `--sample=-5`: `df.sample(n=-5)` → ValueError cru de pandas.
- **Repro**: `fastslr preview articles.csv -c config.json --sample 0` → tabela vazia; `--sample=-5` → ValueError.
- **Fix sugerido**: `typer.Option(min=1)` ou checagem manual com mensagem amigável + Exit(1) antes de chamar preview_triage.
- **Coberto por teste**: Não.

### run-config-validation-before-terms-exists-traceback (variantes de crash-runtime)

> [!note] Crashes de traceback cru por input malformado (consolidados)
> Vários findings (`raw-traceback-empty-or-unparseable-csv`, `raw-traceback-malformed-json-config`, `diff-no-exists-check`, `new-project-invalid-preset-traceback`, `preview-coverage-no-config-exists-check`) compartilham a mesma causa-raiz: ausência de tratamento de erro na CLI. Listados a seguir individualmente como média/baixa.

### raw-traceback-empty-or-unparseable-csv — CSV vazio/ilegível gera traceback cru (ValueError) em run/preview/coverage

- **Severidade**: Média (rebaixada de alta — UX, exit 1 já correto)
- **Categoria**: crash-runtime
- **Local**: `src/fastslr/core/io.py:152` (raise ValueError); run só valida input_file.exists() em cli.py:191
- **Descrição**: run/preview/coverage só checam existência, não carregabilidade. CSV de 0 bytes faz load_table_safe levantar ValueError que escapa como traceback rich. inspect_run_setup já trata o mesmo caso amigavelmente (controller.py:284-298).
- **Repro**: `printf '' > empty.csv; python -m fastslr run empty.csv -c ... -t ... --quiet < /dev/null` → ValueError com traceback.
- **Fix sugerido**: Capturar ValueError/FileNotFoundError de load_table_safe nos controllers (run_triage/preview_triage/analyze_coverage) ou no cli, traduzir via t() + Exit(1). Reutilizar o padrão de inspect_run_setup.
- **Coberto por teste**: Não.

### raw-traceback-malformed-json-config — config.json malformado gera traceback cru (JSONDecodeError) em run/coverage

- **Severidade**: Média (rebaixada de alta — UX, doctor já trata)
- **Categoria**: crash-runtime
- **Local**: `src/fastslr/core/config.py:33-34` (json.load sem try/except em load_config)
- **Descrição**: load_config faz json.load sem tratamento. JSON inválido (vírgula extra) propaga JSONDecodeError como traceback. new-project instrui "edite os limiares" → erro de sintaxe é comum.
- **Repro**: config.json inválido + `python -m fastslr run ... -c bad.json --quiet < /dev/null` → JSONDecodeError com traceback.
- **Fix sugerido**: Envolver json.load em try/except json.JSONDecodeError, relevantar como erro de config amigável (arquivo, linha, coluna). Tratar na CLI com t() + Exit(1).
- **Coberto por teste**: Não.

### csv-block-case-sensitive-silent-ignore — Bloco do CSV com case diferente de BLOCK_ORDER é ignorado (apenas warning)

- **Severidade**: Média (rebaixada para baixa — CLI já avisa+bloqueia; silencioso só no botão Run da TUI)
- **Categoria**: ux-erro-usuario
- **Local**: `src/fastslr/core/config.py:340-352` (warn) e `419-456` (merge com get exato)
- **Descrição**: Correspondência CSV↔BLOCK_ORDER é case-sensitive sem strip semântico. CSV com 'ctx' e BLOCK_ORDER ['CTX'] → domain_blocks=[] e todos os termos do bloco descartados. **Correção ao finding**: na CLI o `run` roda validate_config ANTES, imprime o warning (nomeando o bloco) e exige confirmação (default=False) — não é silencioso. Caminho realmente silencioso = botão Run direto da TUI. Ver [[Configuração - config e termos]].
- **Repro**: CSV `'ctx,pos,quantum,1,any,0'` + BLOCK_ORDER ['CTX'] → _domain_blocks=[] e warning.
- **Fix sugerido**: Normalizar para comparação case-insensitive (`.strip().upper()` ou mapa canônico) em config.py:340-352 e 419-456, OU fazer a TUI start_triage rodar inspect_run_setup como a CLI.
- **Coberto por teste**: Não.

### i18n-detect-locale-deprecated-getdefaultlocale — detect_locale usa locale.getdefaultlocale() (deprecado, removível em 3.15)

- **Severidade**: Média (rebaixada para baixa — débito técnico; **premissa "3.13+" é incorreta, é 3.15**)
- **Categoria**: config-setup
- **Local**: `src/fastslr/i18n/__init__.py:87`
- **Descrição**: `detect_locale` chama `locale.getdefaultlocale()`, deprecado, com remoção prevista para Python 3.15 (não 3.13). Verificado empiricamente: em 3.11/3.14 a função continua presente e retorna valor; o import não quebra. `set_locale(detect_locale())` roda no import. É débito de manutenção, não bug alcançável hoje (requires-python >=3.10).
- **Repro**: Em Python 3.15+, importar fastslr.i18n e observar comportamento divergente (atualmente só DeprecationWarning).
- **Fix sugerido**: Substituir por `locale.getlocale()` ou parsing direto de LC_ALL/LC_MESSAGES/LANG, mantendo fallback para DEFAULT_LOCALE. Adicionar teste de detect_locale.
- **Coberto por teste**: Não.

### false-empty-kind-warnings-normalization-rows — doctor/run rotulam 34 regras de normalização válidas como 'Row skipped'

- **Severidade**: Média (rebaixada para baixa — cosmético, regras funcionam)
- **Categoria**: ux-erro-usuario
- **Local**: `src/fastslr/core/config.py:200-212` (loop reprocessa linhas já consumidas em 183)
- **Descrição**: As 34 linhas GLOBAL com normalization_type têm kind vazio intencionalmente; são extraídas em config.py:183 mas o loop emite "Row N: empty kind. Row skipped." para cada. O usuário vê 34 avisos sugerindo que ~1/3 da config foi descartada, quando as regras estão ativas. Dispara out-of-the-box com os dados do projeto. **Co-causa do finding run-aborts-on-spurious-warnings**.
- **Repro**: `python -m fastslr doctor --input data/Final_Corpus.csv -c .../default_config.json -t data/terms_final.csv` → 34 linhas "Row 2..35: empty kind. Row skipped.".
- **Fix sugerido**: Pular silenciosamente (continue sem warning) linhas com `normalization_type` preenchido. Reservar 'empty kind' só para linhas sem kind E sem normalization_type.
- **Coberto por teste**: Não.

### preview-coverage-no-config-exists-check — preview e coverage não validam existência do config (FileNotFoundError cru)

- **Severidade**: Média (rebaixada para baixa — mensagem da exceção já informativa)
- **Categoria**: crash-runtime
- **Local**: `src/fastslr/app/cli.py:242-288` (não checam config.exists(), ao contrário de run em cli.py:195)
- **Descrição**: run trata config inexistente amigavelmente, mas preview/coverage não → load_config levanta FileNotFoundError cru. Inconsistência entre comandos com os mesmos parâmetros.
- **Repro**: `python -m fastslr preview data/Final_Corpus.csv -c nao_existe.json -t ... < /dev/null` → FileNotFoundError com traceback.
- **Fix sugerido**: Helper único de validação de existência/parse de config+input usado por run/preview/coverage/diff, com mensagens consistentes e Exit(1).
- **Coberto por teste**: Não.

### doctor-not-localized-mixed-language — Saída do doctor é sempre inglês enquanto o resto da CLI segue o locale (pt_BR)

- **Severidade**: Média (rebaixada para baixa — cosmético, sem impacto funcional)
- **Categoria**: ux-erro-usuario
- **Local**: `src/fastslr/app/cli.py:94-135` (_print_setup_inspection com strings hardcoded em inglês); i18n auto-detecta locale em `i18n/__init__.py:121`
- **Descrição**: `set_locale(detect_locale())` no import detecta pt_BR, então run/preview/etc. ficam em português. Mas `_print_setup_inspection` usa literais em inglês ('Setup errors', 'Domain blocks', 'Valid terms', 'Run command') sem t(); as chaves não existem nos locales. Idioma misturado para usuário pt_BR.
- **Repro**: Sistema pt_BR: `python -m fastslr doctor ...` → cabeçalhos em inglês; `python -m fastslr preview ...` → português.
- **Fix sugerido**: Substituir literais de _print_setup_inspection e mensagens de inspeção/avisos por t() com chaves nos 3 locales (en/pt_BR/es).
- **Coberto por teste**: Não.

---

## 🟢 Severidade Baixa

### diff-no-exists-check — diff não valida existência dos arquivos (FileNotFoundError cru)

- **Severidade**: Baixa
- **Categoria**: crash-runtime
- **Local**: `src/fastslr/app/cli.py:291-301` (diff não chama .exists())
- **Descrição**: Único comando consumidor de arquivos sem checagem .exists() (run/config/preview/export todos fazem). Erro de digitação de caminho → FileNotFoundError cru.
- **Repro**: `python -m fastslr diff nope1.xlsx nope2.xlsx < /dev/null` → FileNotFoundError com traceback.
- **Fix sugerido**: Checagem .exists() para ambos os argumentos no início do diff, com `t('file_not_found')` + Exit(1).
- **Coberto por teste**: Não.

### new-project-invalid-preset-traceback — new-project com --preset inválido gera traceback cru (ValueError)

- **Severidade**: Baixa
- **Categoria**: crash-runtime
- **Local**: `src/fastslr/core/presets.py:34` (raise ValueError 'Unknown preset'); new-project em cli.py:325-363 não valida preset
- **Descrição**: `--preset` aceita string livre e só descobre que é inválido no fundo (presets.py), onde ValueError escapa como traceback. Efeito colateral: o mkdir do output_dir (controller.py:510) ocorre ANTES da validação (511), criando diretório-fantasma.
- **Repro**: `python -m fastslr new-project P2 -b 'A,B' -p banana -o ...` → ValueError com traceback.
- **Fix sugerido**: Validar preset no início (typer Enum/choice) ou capturar ValueError → Exit(1) com t(). Mover mkdir para depois da validação.
- **Coberto por teste**: Não.

### find-positive-terms-int-level-crash — int(level) sem proteção em find_positive_terms pode lançar ValueError

- **Severidade**: Baixa
- **Categoria**: crash-runtime
- **Local**: `src/fastslr/core/scoring.py:82-84` (find_positive_terms) e `171`
- **Descrição**: `found_levels.add(int(level))` — o try/except em volta só captura `re.error`, não ValueError/TypeError. Com level não-numérico crasha. **Não alcançável no pipeline**: precompile_patterns (patterns.py:143-146) coage level inválido para None. É hardening de API pública (em `__all__`).
- **Repro**: `find_positive_terms('foo','','', [{'pattern':re.compile('foo'),'level':'notanumber',...}])` → ValueError.
- **Fix sugerido**: try/except (ValueError, TypeError) em volta de int(level), ou checar isdigit, ignorando nível inválido.
- **Coberto por teste**: Não.

### id-output-key-collision — id_output configurável pode colidir com colunas geradas e sobrescrever o ID

- **Severidade**: Baixa
- **Categoria**: robustez
- **Local**: `src/fastslr/core/engine.py:269-298` (row_output) e `319`
- **Descrição**: row_output é `{id_output: article_id}`; depois `update(...)` adiciona Final_Decision/Status_<bloco>/etc. Se `fields.id_output` for um desses nomes, o update sobrescreve o ID silenciosamente. **Não exposto na TUI/CLI** — só editando o JSON a mão; default 'ID' nunca colide.
- **Repro**: `fields.id_output='Final_Decision'` → ID 'a' perdido (sobrescrito por ['REJECTED_FINAL']).
- **Fix sugerido**: Validar id_output contra nomes reservados/gerados na carga de config e levantar erro claro, ou prefixar; no mínimo logar warning.
- **Coberto por teste**: Não.

### required-columns-no-header-normalization — Colunas obrigatórias exigem nome exato; cabeçalho com caixa/espaço falha

- **Severidade**: Baixa
- **Categoria**: ux-erro-usuario
- **Local**: `src/fastslr/core/config.py:168-170` (`required_cols.issubset(set(df.columns))`)
- **Descrição**: Validação usa 'block','kind','term' exatos sem normalizar caixa/espaço. Cabeçalho 'Block', 'TERM' ou 'term ' → ValueError 'missing required columns'. A mensagem não lista as colunas encontradas. Mitigado pelo README que documenta o cabeçalho canônico minúsculo. Ver [[Configuração - config e termos]].
- **Repro**: CSV com cabeçalho 'Block;Kind;Term;...' → ValueError apesar de semanticamente válido.
- **Fix sugerido**: Normalizar df.columns (strip+lower) após load_table_safe e comparar via conjunto normalizado; incluir colunas encontradas na mensagem de erro.
- **Coberto por teste**: Não.

### proximity-token-unit-injection — token_unit de GlobalParams é interpolado cru no regex (injeção/erro de padrão)

- **Severidade**: Baixa
- **Categoria**: robustez
- **Local**: `src/fastslr/core/patterns.py:60`; `src/fastslr/core/config.py:133`
- **Descrição**: `token_unit` (default `\S+`) vem de `str(global_cfg.get('TOKEN_UNIT_FOR_GAPS', ...))` e é interpolado sem escape. `'(['` → compile_proximity_pattern retorna None (proximidade silenciosamente desligada); `'.*'` → gap guloso (over-matching). Exige misconfiguração deliberada do JSON.
- **Repro**: `token_unit_for_gaps='(['` → None para todos os pares; `'.*'` → gap guloso.
- **Fix sugerido**: Validar `re.compile` do fragmento no carregamento e cair para `\S+` com warning se inválido. Documentar como campo regex avançado.
- **Coberto por teste**: Não.

### broad-terms-strict-gt-corpus-pequeno — broad-terms usa > estrito contra total*0.8; corpus de 1 artigo marca todo termo como broad

- **Severidade**: Baixa
- **Categoria**: bug-logica
- **Local**: `src/fastslr/core/coverage.py:96,99`
- **Descrição**: `broad_threshold = total*0.8`; condição `article_count > broad_threshold`. Para total=1, threshold=0.8 → qualquer termo com 1 hit (1>0.8) é broad 100%. Falta piso mínimo de corpus. **Repro do finding original incorreto**: preview_triage NÃO chama analyze_term_coverage; só alcançável via `fastslr coverage` sobre arquivo de 1-2 artigos (uso degenerado).
- **Repro**: `analyze_term_coverage` com result_df de 1-2 artigos → todos os termos casados viram broad.
- **Fix sugerido**: Guarda de tamanho mínimo de corpus (não calcular broad-terms se total < N, ex. 10/20) e/ou mínimo absoluto de article_count.
- **Coberto por teste**: Não.

### export-academic-no-validation-empty-package — export aceita arquivo que não é resultado e gera pacote enganoso

- **Severidade**: Baixa
- **Categoria**: robustez
- **Local**: `src/fastslr/app/cli.py:367-389`; `controller.py:586-616` (export_academic_package)
- **Descrição**: export_cmd só checa .exists(); export_academic_package não valida que o arquivo é resultado FastSLR (não checa Final_Decision). Apontar para CSV qualquer gera ZIP "com sucesso" com arquivo arbitrário + protocol.json/report do diretório — pacote acadêmico inválido sem aviso. Ver [[Reprodutibilidade e Pacote Acadêmico]].
- **Repro**: `fastslr export articles_brutos.csv -o out/` → academic_package.zip criado com mensagem de sucesso, sem resultados reais.
- **Fix sugerido**: Em export_academic_package, ler com read_result_table e avisar/abortar se faltar Final_Decision; ou warning na CLI.
- **Coberto por teste**: Não.

### browse-terms-shows-precompiled-mismatch-note — browse_terms ignora _parse_warnings (linhas puladas não exibidas)

- **Severidade**: Baixa
- **Categoria**: ux-erro-usuario
- **Local**: `src/fastslr/app/controller.py:631-694` (browse_terms); `cli.py:392-433` (terms_cmd)
- **Descrição**: terms_cmd descarta os avisos de parsing. parse_terms_csv acumula `_parse_warnings` (kind inválido, term vazio, nível fora do range), mas browse_terms/terms_cmd nunca os exibem — o usuário assume que todas as linhas foram aceitas. **Atenuante**: os avisos SÃO surfaceados pelo comando `validate`. A suspeita original de mutação de estado foi refutada (não há mutação).
- **Repro**: `fastslr terms -c config.json -t terms.xlsx` com linhas inválidas → tabela só com termos válidos, sem aviso.
- **Fix sugerido**: Propagar `config.get('_parse_warnings', [])` no TermsView e exibir em terms_cmd (seção 'Avisos de parsing').
- **Coberto por teste**: Não.

### i18n-format-valueerror-uncaught — _() só captura KeyError/IndexError; ValueError de format spec quebraria a UI

- **Severidade**: Baixa (rebaixada de alta — nenhum caminho de uso normal dispara o ValueError)
- **Categoria**: crash-runtime
- **Local**: `src/fastslr/i18n/__init__.py:111-116`
- **Descrição**: O except em `_()` captura só (KeyError, IndexError). Strings tipadas (`speed_unit='{value:.1f}...'`, `time_unit='{value:.2f}s'`) lançam ValueError com valor não-numérico. **Não alcançável**: os 2 call sites de produção (cli.py:73,77) passam `stats.get(..., 0)` numérico garantido pelo engine. É hardening defensivo.
- **Repro**: `_('Value {v:.2f}', v='not a number')` → ValueError não tratado.
- **Fix sugerido**: Ampliar o except para (KeyError, IndexError, ValueError) e logar via logger.debug a falha de formatação.
- **Coberto por teste**: Não (zero testes de i18n).

### profiles-empty-name-hidden-file — Nome de perfil vazio/espaços gera arquivo oculto '.json'

- **Severidade**: Baixa (rebaixada de média)
- **Categoria**: ux-erro-usuario
- **Local**: `src/fastslr/app/profiles.py:34, 55, 95`
- **Descrição**: `name=''` → safe_name='' → caminho '.json' (oculto em Unix); `name='   '` → '___.json'. Sem validação. Alcançável só via CLI com input deliberado (TUI não salva). Relacionado a profiles-path-traversal e profiles-silent-overwrite.
- **Repro**: `profiles.save_profile('', {})` → cria `~/.fastslr/profiles/.json` sem erro.
- **Fix sugerido**: Validar nome sanitizado não-vazio em save/load/delete (`raise ValueError`). Avisar/confirmar antes de sobrescrever.
- **Coberto por teste**: Não.

### profiles-silent-overwrite — save_profile sobrescreve perfil existente sem aviso (colisão por normalização)

- **Severidade**: Baixa (rebaixada de média)
- **Categoria**: ux-erro-usuario
- **Local**: `src/fastslr/app/profiles.py:31-49`
- **Descrição**: `write_text` incondicional. 'My Profile', 'my profile', 'MY_PROFILE' → todos 'my_profile.json'; o 2º save apaga o config do 1º sem aviso. O aspecto surpreendente é a colisão por normalização (sobrescrever pelo mesmo nome é semântica esperada de save).
- **Repro**: `save_profile('My Profile', cfg1); save_profile('my profile', cfg2)` → cfg1 perdido.
- **Fix sugerido**: Detectar colisão de safe_name distinta do nome original (avisar quando o destino já pertence a um perfil com _profile_name diferente); flag overwrite deixando TUI/CLI confirmar.
- **Coberto por teste**: Não.

### tui-settings-locale-empty-no-feedback — SettingsScreen.apply_settings ignora silenciosamente idioma vazio/BLANK

- **Severidade**: Baixa
- **Categoria**: ux-erro-usuario
- **Local**: `src/fastslr/app/tui.py:932-938`
- **Descrição**: `apply_settings` lê `lang = Select.value` e só age `if lang:`. Com Select.BLANK (falsy — e é a 1ª linha do dropdown quando allow_blank=True, default), nenhum branch executa: nem set_locale nem mensagem. Clicar Apply não faz nada.
- **Repro**: Tela Settings, Select em branco, clicar Apply → nenhuma mudança/feedback.
- **Fix sugerido**: Branch else atualizando #settings_msg ('Selecione um idioma válido'); ou `allow_blank=False` no Select.
- **Coberto por teste**: Não.

### tui-results-detail-cursor-row-empty — Filtro 'Approved' ignorado silenciosamente quando falta coluna Final_Decision

- **Severidade**: Baixa
- **Categoria**: ux-erro-usuario (categoria original 'crash-runtime' incorreta — não há crash; índices já guardados)
- **Local**: `src/fastslr/app/tui.py:549-560, 586-607`
- **Descrição**: Em load_results (tui.py:509) o filtro só é aplicado se `'Final_Decision' in df.columns`; quando filter != 'all' e a coluna não existe, o filtro é silenciosamente ignorado e o usuário vê TODAS as linhas. As alegações de crash de indexação são falso-positivo (estão guardadas por `if row_index >= len(df)`).
- **Repro**: Carregar results file sem Final_Decision e selecionar filtro 'Approved' → mostra todas as linhas sem avisar.
- **Fix sugerido**: Quando filter != 'all' e 'Final_Decision' ausente, `self.notify` avisando que o arquivo não tem decisões para filtrar.
- **Coberto por teste**: Não.

### tui-empty-input-silent-return — Vários handlers fazem 'return' silencioso com input vazio sem feedback

- **Severidade**: Baixa
- **Categoria**: ux-erro-usuario
- **Local**: `src/fastslr/app/tui.py:427-428, 502-503, 793-794`
- **Descrição**: BrowseTermsScreen.load_terms, ResultsScreen.load_results e EditConfigScreen.load_config fazem `if not <path>: return` sem mensagem. Clicar Load com campo vazio não faz nada — inconsistente com outras telas (Coverage/Diff/Export) que usam `self.notify(severity='warning')`.
- **Repro**: Browse Terms/Results/Edit Config: clicar load com campo vazio → nenhuma reação.
- **Fix sugerido**: Trocar os 'return' por `self.notify('Informe o caminho do arquivo...', severity='warning')`.
- **Coberto por teste**: Não.

### tui-settings-locale-not-applied-current-screen — Mudança de idioma não re-renderiza telas montadas; maior parte da UI é inglês hardcoded

- **Severidade**: Baixa
- **Categoria**: ux-erro-usuario
- **Local**: `src/fastslr/app/tui.py:926-938`
- **Descrição**: set_locale altera _strings global mas widgets já compostos não são recompostos. Grande parte do texto da TUI é hardcoded em inglês no compose ('Run Triage', 'Choose your articles file', botões 'Cancel'/'Create Project') e NUNCA passa por t(). i18n cobre quase só tabelas/mensagens de resultado. O Select usa value='en' fixo ignorando o locale corrente.
- **Repro**: Trocar idioma para pt_BR em Settings e navegar → títulos/prompts/botões seguem em inglês.
- **Fix sugerido**: Envolver literais de UI em t() com chaves dedicadas nos 3 locales; inicializar o Select com get_locale() em vez de 'en' fixo.
- **Coberto por teste**: Não.

### default-config-csv-false-vs-codigo-true — Default de export divergente (default_config.json csv:false/xlsx:true vs get_export_opts csv:true)

- **Severidade**: Baixa
- **Categoria**: config-setup
- **Local**: `src/fastslr/core/io.py:204-218`
- **Descrição**: `get_export_opts` usa `bool(out.get('csv', True))` e `bool(out.get('xlsx', False))` — sem bloco 'output' exporta CSV e não XLSX. default_config.json e generate_config definem o oposto (csv:false, xlsx:true). Caminhos suportados (template/new-project) sempre trazem o bloco output, então o fallback só vaza para config mínimo escrito a mão.
- **Repro**: run com config mínima sem bloco output → .csv; com default_config.json → .xlsx.
- **Fix sugerido**: Alinhar o default in-code de get_export_opts com o template (csv:false/xlsx:true).
- **Coberto por teste**: Não (testes sempre passam bloco output explícito).

### default-config-fora-do-pacote-fixture-teste — default_config.json só é usado como fixture de teste via caminho relativo ao src

- **Severidade**: Baixa
- **Categoria**: reprodutibilidade
- **Local**: `tests/test_engine.py:22-26`
- **Descrição**: Nenhum código de runtime referencia 'default_config'. Único consumidor é test_engine.py via caminho relativo à árvore-fonte. (1) É uma 4ª fonte de defaults que confunde (risco de drift vs constants.py); (2) o teste só passa rodando in-tree. A quebra contra pacote instalado é hipotética (fluxo padrão é pythonpath=['src'] in-tree).
- **Repro**: grep por 'default_config' em src/ → zero usos de runtime.
- **Fix sugerido**: Decidir o papel: se template de runtime, carregar via importlib.resources e empacotar; se fixture, mover para tests/fixtures/. Em ambos, unificar defaults com constants/presets.
- **Coberto por teste**: Não.

### versao-duplicada-mao — VERSION mantida manualmente em dois lugares (constants.py e pyproject.toml)

- **Severidade**: Baixa
- **Categoria**: reprodutibilidade
- **Local**: `src/fastslr/core/constants.py:5`
- **Descrição**: '3.0.0' hardcoded em constants.py:5 (reexportado como __version__) E em pyproject.toml:7. Coincidem hoje, mas mantidas a mão. constants.py alimenta protocol.json/relatórios (triage_version); pyproject alimenta PKG-INFO/pip show. Bump de uma sem a outra compromete rastreabilidade de qual versão gerou um artefato acadêmico. Não confundir com PROTOCOL_VERSION_CURRENT='2.1' (versão de schema, legitimamente separada). Ver [[Reprodutibilidade e Pacote Acadêmico]].
- **Repro**: Bumpar pyproject para 3.0.1 sem tocar constants.py → pip show diz 3.0.1, protocol.json diz 3.0.0.
- **Fix sugerido**: `[tool.setuptools.dynamic] version={attr='fastslr.core.constants.VERSION'}` (fonte única). Teste `assert __version__ == importlib.metadata.version('fastslr')`.
- **Coberto por teste**: Não.

### empty-corpus-silent-success — Corpus só com cabeçalho (0 artigos) gera 'sucesso' silencioso com pacote/relatório vazios

- **Severidade**: Baixa
- **Categoria**: robustez
- **Local**: `src/fastslr/app/controller.py` run_triage / `cli.py` run (sem checagem de 0 linhas)
- **Descrição**: CSV só com header roda com exit 0 e produz triage_results.xlsx vazio, academic_package.zip e triage_report.txt com 'TOTAL ARTICLES: 0', sem aviso. `--quiet` pula o gate de confirmação. O resultado é tecnicamente correto (0 entra, 0 sai) mas o usuário que exportou corpus errado recebe entregáveis "válidos" vazios.
- **Repro**: `printf '"Key","Title","Abstract Note"\n' > header_only.csv; python -m fastslr run header_only.csv -c ... -t ... -o ho --quiet < /dev/null` → exit 0, 'TOTAL ARTICLES: 0'.
- **Fix sugerido**: Detectar DataFrame de entrada vazio (0 linhas após carga) e emitir aviso/erro claro antes de gerar artefatos.
- **Coberto por teste**: Não (test_empty_dataframe codifica o oposto — sucesso silencioso).

---

## Falso-positivos / Refutados

Findings **não confirmados** após verificação. Não re-investigar — motivo resumido em uma linha cada.

- **min-approved-blocks-zero-coerced-to-one** (scoring): A coerção `0 or 1 == 1` é factual mas não muda decisão alcançável — linhas 425/430 já classificam FLAGGED/REJECTED independente de min_approved; "aprovar sem blocos aprovados" é estruturalmente impossível.
- **strict-policy-empty-rejected-reason-not-evaluated-mask** (scoring): Razão 'Rejected blocks: ' vazia exige APPROVED+NOT_EVALUATED sem REJECTED — combinação inalcançável pelo engine (NOT_EVALUATED só surge com fail-fast/T0, que sempre implicam um REJECTED ou curto-circuito).
- **section-cap-applied-before-weight-doc-ok-but-uplift-after-cap** (scoring): O próprio finding admite "não é bug, comportamento documentado"; cap-antes-do-peso e uplift batem com [[Algoritmo - Pontuação (Scoring)]]. É flag de calibragem, não defeito.
- **automap-int-column-crash** (engine): AttributeError em `actual_col.lower()` só com colunas inteiras; load_table_safe sempre usa header=0 → rótulos str. Repro constrói DataFrame cru ignorando a ingestão.
- **duplicate-column-isna-ambiguous** (engine): pandas 2.0+ deduplica rótulos repetidos obrigatoriamente ('title','title.1'); um arquivo real nunca produz colunas idênticas. Só via DataFrame construído à mão.
- **tags-list-isna-before-isinstance** (engine): O ramo list/tuple é dead code inofensivo; com dtype=str + keep_default_na=False toda célula é string — uma lista jamais alcança a linha 227.
- **score-distribution-astype-float-fragile** (engine): astype(float) só crasharia com string em FinalScore_*, mas o produtor é `round(ev.final_score,2)` (float garantido por models.py); string nunca chega.
- **t0-shortcircuit-empty-blocks-rejected** (engine): validate_config emite error "No domain blocks defined" e a CLI aborta com Exit(1) antes de process_articles; REJECTED_FINAL é fallback defensivo inalcançável via uso normal.
- **auto-detect-input-ambiguous-fallback** (config): auto_detect_input é DEAD CODE (0 call sites); a CLI recebe arquivo direto via typer.Argument, nunca um diretório.
- **dead-isna-checks-keepdefaultna-false** (config): Checagens pd.isna redundantes mas inofensivas; block/kind/term já são str(...).strip() antes, e keep_default_na=False garante '' não NaN.
- **wildcard-stops-at-hyphen-space** (patterns): A lógica de decisão usa `pattern.search` como teste booleano — 'data-driven'/'data mining'/'database' todos retornam True; o span estreito só afeta highlight cosmético.
- **compound-or-overmatches-broadens** (patterns): Comportamento intencional, documentado em TECHNICAL.md e testado (test_or_connector); 'or' é separador uniforme com and/&//; controlável via enable_proximity_detection.
- **invalid-positive-regex-silent-drop** (patterns): Falso — `if warnings is not None and is_regex` dispara para positivo E anti; regex inválida em positivo JÁ gera warning. ReDoS é auto-infligido (regex do próprio operador) sobre texto curto.
- **wildcard-mid-term-and-multiple** (patterns): Padrões '*tion'→`\b\w*tion\b` etc. são válidos e semanticamente corretos; `\b`+`\w*` é a forma canônica de match de palavra. O próprio finding admite 'inofensivo, severity baixa'.
- **cache-key-redundant-str** (normalization): Double-coerção `str(text)` puramente cosmética; o único caller (_normalize_sections) garante str não-vazia via `x or ""` + `.strip()` — NaN jamais chega.
- **abbrev-ignorecase-pre-lowercase** (normalization): IGNORECASE NÃO é redundante (o .lower() do texto só ocorre depois); comportamento correto e travado por testes. Falso-positivo como bug, válido só como nit cosmético.
- **highlight-text-upper-destrutivo** (io-coverage): `.upper()` é ênfase visual INTENCIONAL e documentada (TECHNICAL.md §10); casing original preservado nas colunas-fonte. Distorção de acrônimos é cosmética em coluna auxiliar.
- **highlight-asterisco-aninhado** (io-coverage): highlight_text é chamado UMA vez por campo sobre texto cru; não há reprocessamento na pipeline. Nenhum consumidor parseia '***'.
- **csv-sep-detection-tie-min-columns** (io-coverage): Refutado empiricamente — pandas respeita aspas, separador errado colapsa <min_columns e é descartado; nenhum caller usa min_columns=2 com input de 2 colunas.
- **dead-terms-comparacao-ok-mas-fragil** (io-coverage): Caminho normal usa original_term nos dois lados → sem falso dead-term; o único caso real (aspas) é duplicata do finding highlight-term-quote-breaks-coverage-parse.
- **appendix-pack-zip-strict-nome-colisao** (io-coverage): Colisão de path.name não alcançável (callers usam basenames fixos distintos; dedup por resolve() cobre o caso real); zip(strict=True) é guard morto cosmético.
- **i18n-silent-swallow-masks-bugs** (tui-i18n): Todos os call sites passam o placeholder correto (path=); o branch de swallow só dispara com kwargs errados — código de chamada incorreto, não uso normal.
- **i18n-detect-locale-unvalidated-env** (tui-i18n): FASTSLR_LANG cru é sanitizado pelo único consumidor (set_locale), que faz match/prefixo/fallback 'en'; valor inválido nunca produz comportamento incorreto.
- **run-timestamp-quebra-diff-determinismo** (setup-packaging): diff_results projeta só [id, Final_Decision] — run_timestamp nunca é lido; 'deterministic' refere-se às decisões, e run_timestamp é explicitamente excluído nas checagens (ver [[Validação - Checklist]]).
- **ruff-format-12-files-drift** (dynamic-quality): Causa errada — é normalização CRLF↔LF do autocrlf no Windows; os blobs commitados em LF passam no formatter. Resíduo menor: falta .gitattributes eol=lf.
- **pyright-chardet-missing-import** (dynamic-quality): Import protegido por try/except + guard `if chardet is None`; risco de runtime zero. Diagnóstico depende do ambiente (extra opcional não instalado), não do código.
- **pyright-pandas-int-idx-hashable** (dynamic-quality): iterrows sobre DataFrames de load_table_safe (sem index_col) → sempre RangeIndex int; int(idx) seguro em runtime. Só nit de anotação.
- **pyright-pandas-isna-conditional-ndframe** (dynamic-quality): pandas deduplica cabeçalhos → escalar str, pd.isna retorna bool real; crash 'Series ambiguous' só com DataFrame manual. Ruído de type-checker.
- **module-not-found-without-install** (dynamic-cli): Refutado — existe `src/fastslr/__main__.py`; `python -m fastslr version` retorna 'FastSLR v3.0.0'. Nenhuma doc instrui rodar da raiz sem install; README documenta pip install -e.

---

## 📋 Plano de Correção Priorizado

Ordem recomendada de aplicação, agrupada por severidade e por dependência técnica. Cada item: arquivo-alvo, abordagem TDD (teste primeiro), esforço estimado. **Princípio geral**: escrever o teste de regressão (que reproduz o bug e falha) ANTES da correção, dado que praticamente nenhum finding tem cobertura.

### Fase 0 — Pré-requisito transversal (desbloqueia validação de quase tudo)

1. **Criar `tests/test_cli.py` com `typer.testing.CliRunner`** — não existe NENHUM teste de CLI hoje. É dependência de fato para validar os findings de UX/crash-runtime (run/preview/coverage/diff/new-project/profile). Esforço: **médio**. Sem alvo de código, mas habilita TDD de toda a Fase 3.

### Fase 1 — Alta severidade, lógica de matching (núcleo da triagem)

2. **Corrigir `\b` em patterns.py e normalization.py** (boundaries condicionais) — **resolve em conjunto**: `word-boundary-nonword-suffix-fails` (patterns.py:35), `symbol-wordboundary-broken` (normalization.py:71-73), `symbol-pass-after-lowercase-uppercase-key-dead` (lowercasear chave), e mitiga `silent-mismatch-term-vs-article`. **Dependência**: fazer junto, pois compartilham a mesma raiz (`\b` ancorado em char não-word). TDD: testes para C++, C#, .NET, F#, r&d (devem falhar antes). Esforço: **alto**.
3. **Guarda da regra especial** `and len(approved_blocks) >= 1` — `special-rule-single-flagged-block-vacuous-approve` (scoring.py:451-457). TDD: teste bloco único FLAGGED → deve ser FLAGGED_FINAL. Esforço: **baixo**.
4. **Score 0 / nível fora do range → REJECTED** — **resolve em conjunto** `flagging-threshold-default-zero-flags-zero-score` (scoring.py:292,297) e `out-of-range-level-flagged-zero-score` (config.py:243-249 `level=''`). TDD: termo nível 6 fora do range → REJECTED, não FLAGGED. Esforço: **baixo/médio**.

### Fase 2 — Alta severidade, robustez de I/O e packaging

5. **Encoding fallback determinístico na leitura** — **resolve em conjunto** `detect-encoding-chardet-ausente-cp1252` (io.py:99-104,141-152) e `chardet-opcional-muda-resultado`. Cadeia utf-8-sig→cp1252→latin-1 consultando config.encoding, independente de chardet; mensagem mencionando encoding. TDD: fixture cp1252 'Café;Über' deve carregar. Esforço: **médio**.
6. **package-data no pyproject.toml** — `package-data-nao-incluido-no-build` (pyproject.toml:32-33) + migrar i18n para importlib.resources. TDD: teste que verifique presença de locales no wheel (ou que importlib.resources resolve os locales). Esforço: **baixo/médio**.
7. **Sanitização de nome de perfil** — **resolve em conjunto** `profiles-path-traversal` + `profiles-empty-name-hidden-file` + `profiles-silent-overwrite` (profiles.py:34,55,95). `re.sub([^a-z0-9_-]+)`, rejeitar vazio, validar is_relative_to, detectar colisão. TDD: '../../../evil' deve levantar ValueError. Esforço: **baixo**.

### Fase 3 — Alta/média severidade, UX e tratamento de erros na CLI

8. **Handler global de exceções na CLI** — `no-global-exception-handler` (cli.py:30-35, __main__.py). É a **causa-raiz transversal** de quase todos os crash-runtime: ao resolvê-lo (wrapper `main()` ou result_callback capturando FileNotFoundError/ValueError/JSONDecodeError), **resolve ou mitiga em cascata**: `preview-coverage-terms-raw-traceback-missing-files`, `diff-id-fallback-keyerror`, `diff-no-friendly-error-for-valueerror`, `diff-no-exists-check`, `run-config-validation-before-terms-exists-traceback`, `run-terms-missing-not-validated`, `raw-traceback-empty-or-unparseable-csv`, `raw-traceback-malformed-json-config`, `new-project-invalid-preset-traceback`, `preview-coverage-no-config-exists-check`. **Dependência**: fazer DEPOIS da Fase 0. TDD: cada repro deve produzir Exit(1) + mensagem amigável, sem traceback. Esforço: **médio** (mais os ajustes por comando).
9. **Suprimir avisos falsos de normalização + não abortar não-interativo** — **resolve em conjunto** `false-empty-kind-warnings-normalization-rows` (config.py:200-212) e `run-aborts-on-spurious-warnings-noninteractive` (cli.py:209-215). Pular warning quando normalization_type preenchido; prosseguir em `--quiet`/não-TTY ou exigir `--yes`. TDD: terms_final.csv não deve gerar os 34 avisos; run não-interativo deve completar. Esforço: **baixo/médio**.
10. **diff fillna('MISSING')** — `diff-outer-merge-nan-not-missing` (controller.py:474-484). TDD: IDs exclusivos devem mostrar 'MISSING', não 'nan'. Esforço: **baixo**.
11. **new-project sem overwrite silencioso** — `create-project-silent-overwrite` (controller.py:499-572). Checar existência + `--force`/confirm. TDD: 2ª execução sem --force deve abortar. Esforço: **baixo**.
12. **highlight-term parse robusto** — `highlight-term-quote-breaks-coverage-parse` (io.py:316 + coverage.py:25). json.dumps no pack + regex ajustada. TDD: termo com aspas casado não deve virar dead-term. Esforço: **médio**.

### Fase 4 — Média severidade, qualidade e consistência

13. **Fonte única de threshold L4** — `flagging-threshold-l4-divergence` (+ 2 duplicatas). Alterar constants.py:47 para 4:7, corrigir conftest.py:24, teste de igualdade entre as 3 fontes. Esforço: **baixo**.
14. **Proximidade**: separador ampliado (`proximity-requires-adjacent-space`), clamp max_gap≥0 (`proximity-negative-gap-literal-no-match`), split recursivo (`compound-splits-only-first-separator`) — patterns.py:60,71-89; config.py:132. TDD: 'machine-learning', max_gap=-1, 'A and B and C'. Esforço: **médio**.
15. **Normalização determinística**: ordem por comprimento de chave (`rule-order-dependent-output`), lowercasear valores (`symbol-replacement-value-not-lowercased`), dedup simétrico (`dup-detection-symbol-case-asymmetry`) — normalization.py. Esforço: **médio**.
16. **OrderedDict no cache** (`lru-cache-on-n`), **TUI thread-safe** (`tui-worker-ui-access-from-thread`), **stats denominador** (`stats-inconsistent-denominator-error-rows`), **case-insensitive block** (`csv-block-case-sensitive-silent-ignore`), **deprecação getdefaultlocale** (`i18n-detect-locale-deprecated-getdefaultlocale`), **doctor i18n** (`doctor-not-localized-mixed-language`), **preview --sample min=1** (`preview-sample-zero-silent-empty`), **migrate snapshot gate** (`migrate-protocol-snapshot-incompleto`). Esforço por item: **baixo a médio**.

### Fase 5 — Baixa severidade, hardening e polimento (oportunístico)

17. Itens de baixa severidade: validação de header (`required-columns-no-header-normalization`), validação de token_unit (`proximity-token-unit-injection`), guarda de id_output (`id-output-key-collision`), int(level) defensivo (`find-positive-terms-int-level-crash`), piso de corpus broad-terms (`broad-terms-strict-gt-corpus-pequeno`), validação export (`export-academic-no-validation-empty-package`), warnings em browse_terms (`browse-terms-shows-precompiled-mismatch-note`), feedback TUI (`tui-empty-input-silent-return`, `tui-settings-locale-empty-no-feedback`, `tui-results-detail-cursor-row-empty`), cobertura i18n da TUI (`tui-settings-locale-not-applied-current-screen`), version dinâmica (`versao-duplicada-mao`), default export alinhado (`default-config-csv-false-vs-codigo-true`), empty-corpus guard (`empty-corpus-silent-success`), mover/empacotar default_config.json (`default-config-fora-do-pacote-fixture-teste`), i18n ValueError catch (`i18n-format-valueerror-uncaught`). Esforço cada: **baixo**. Avaliar `export-raw-subset` e `adapters.py` (dead code): remover ou consertar+integrar.

---

Relacionado: [[Validação - Checklist]] · [[Validação - Bugs e Riscos Conhecidos]] · [[Home]]
