# Revisão da 3.1.0: junção da auditoria pré-IP com a 3.0.1

| Campo | Valor |
|---|---|
| **Data** | 2026-10-15 |
| **Para que serve** | Decidir se a 3.1.0 pode ser travada e aplicada na RSL1 e na RSL2 |
| **Comparado** | 3.0.1 (`4a66697`, o lado 3.0.1 da junção, que é a tag `v3.0.1` mais os PRs #9 e #10) contra a 3.1.0 (ramo `merge/desktop-pre-ip`) |
| **Instrumentos** | Regressão em `docs/regressao_v3.1.0/`; revisão multidimensional com adjudicação adversarial; medida de tempo e perfil |

## 1. Veredito

- **RSL1: a triagem é a mesma.** Nos 505 registros históricos, com `config_v8.json` e `terms_final.csv`, nenhuma célula do resultado muda entre a 3.0.1 e a 3.1.0, com e sem palavras-chave. A rodada oficial usa o corpus `b2235fcb…`, e a base confere célula a célula com as rodadas de 2026-10-10 (seção 3.1).
- **Outras configurações: há quebras de comportamento declaradas.** As políticas `strict` e `k_of_n` mudam decisões, de propósito (seção 3.2). As demais quebras estão listadas no CHANGELOG, e nenhuma toca os dados da RSL1.
- **A revisão rodou quatro vezes.**
  - Primeira rodada, sobre a junção: 33 pontos. Os 3 altos foram confirmados por adjudicação adversarial: 2 estão corrigidos, e o terceiro (`strict` e `k_of_n` mudam decisões) foi medido e declarado, porque a mudança é intencional. Dos 30 médios e baixos, 22 foram corrigidos, 2 refutados ou mantidos por decisão anterior, e 6 ficam registrados ou declarados no CHANGELOG.
  - Segunda rodada, sobre esse fechamento: 21 pontos. O alto confirmado está corrigido. Dos 20 restantes, 15 foram corrigidos e 5 ficam registrados ou declarados.
  - Terceira rodada: 24 pontos, com 2 altos que eram o mesmo defeito. As 2 iterações de fechamento estavam esgotadas, e o usuário escolheu estabilizar e fechar (seção 4.3).
  - Quarta e última rodada, sobre a estabilização: 16 pontos, com 2 altos que eram o mesmo defeito. Os 2 altos e 4 dos 14 médios e baixos estão corrigidos; um desses 4 é só na documentação. Os outros 10 ficam declarados no CHANGELOG ou registrados (seção 4.4).
  - As correções da quarta rodada não passaram por uma quinta. Elas foram falsificadas por mutação, e a regressão rodou de novo sobre elas (seções 3.1 e 4.4).
  - O destino de cada achado está na seção 4.
- **Velocidade igual à da 3.0.1**, com crescimento linear (seção 5).

## 2. O que a 3.1.0 junta

- **Auditoria pré-IP (2026-06-10).** Feita sobre a 3.0.0 e nunca publicada: 58 achados em 9 dimensões, 28 correções aprovadas item a item. Ela ficou no desktop, em 9 commits.
- **3.0.1 (2026-10-10).** Auditoria pré-congelamento, achados F01–F10, publicada no PyPI.
- **Conflitos na junção:** 6. Onde as duas auditorias decidiram o mesmo ponto, vale a 3.0.1. Os casos foram:
  - ID repetido: recusa (F08), no lugar do aviso;
  - normalização: as entidades e o markup do pré-IP saem primeiro, depois vêm as regras da 3.0.1;
  - linha do aviso de regex: a do F05.

## 3. Regressão

Método: `prepare_sources.py` monta a base, a junção e uma árvore por módulo desfeito, que é a junção com um módulo de volta à cópia da base. `run_all.py` roda cada árvore pelo caminho de produção (`controller.run_triage`). `compare.py` compara célula a célula, com os números de linha, e atribui a causa de cada diferença ao módulo cuja reversão devolve o valor da base.

Os módulos `config` e `patterns` não podem ser desfeitos sozinhos no código final, porque `io` e `controller` importam deles nomes que a revisão criou (`read_flag`, `ALLOWED_TOKEN_UNITS`). O `compare.py` declara isso no resultado ("could not run alone"). Nenhuma diferença ficou sem causa.

### 3.1 RSL1, política `special`

| Rodada | Corpus | Com palavras-chave | Sem palavras-chave | Referência de 2026-10-10 |
|---|---|---|---|---|
| Oficial, notebook, junção `1e88727` | `b2235fcb…` (505) | 0 registros mudam | 0 registros mudam | 0 células diferentes |
| Oficial, notebook, `2cca7b5` (primeira rodada fechada) | `b2235fcb…` (505) | 0 | 0 | 0 |
| Oficial, notebook, `67a6666` (segunda rodada fechada) | `b2235fcb…` (505) | 0 | 0 | 0 |
| Oficial, notebook, `2987a35` (estabilização) | `b2235fcb…` (505) | 0 | 0 | 0 |
| Oficial, notebook, `afee792` (quarta rodada fechada) | `b2235fcb…` (505) | 0 | 0 | 0 |

A distribuição (aprovados / sinalizados / rejeitados) é 75 / 179 / 251 com palavras-chave e 44 / 154 / 307 sem. As rodadas de `2cca7b5`, `67a6666`, `2987a35` e `afee792` deram o mesmo `regression_detail.json`, byte a byte (SHA-256 `d8d07dfd…`). O compare cobre todas as colunas do resultado, menos `run_timestamp` e `triage_version`, e isso inclui as colunas `*_Highlighted`.

**Piloto da RSL2 (informativo).** São 119 registros (`pilot_dev.csv`, do OpenAlex), com `config_rsl2_rascunho.json` e `terms_rsl2_rascunho_v1.csv`. Em `2cca7b5`, `67a6666`, `2987a35` e `afee792`, 0 registros mudam, e a distribuição é 17 / 25 / 77 (SHA-256 `5ad8e5a7…`). As entidades HTML, o NFKC e o destaque novo não mexeram em nenhuma decisão nem em nenhuma célula.

**Falsificação do instrumento.** Com a v3.0.0 no lugar da base, as decisões finais que mudam são exatamente as da `REGRESSAO_v3.0.1.md`: 583FSDBK e 847Z9MYF com palavras-chave; 2MFBMTMD, 583FSDBK, 847Z9MYF, A4S5QRJZ, H4BYTH8R e MR5HT2NH sem. O instrumento vê diferença onde ela existe.

### 3.2 Políticas `strict` e `k_of_n`

O `config_v8.json` usa a política `special`. Para medir as outras duas, a rodada troca só a `DECISION_POLICY`. Corpus: o do desktop, que reproduz as distribuições e as decisões da rodada oficial.

| Política | Registros que mudam (com / sem palavras-chave) | Decisões finais que mudam | Causa |
|---|---|---|---|
| `strict` | 60 / 59 | com: 23 FLAGGED → REJECTED, 14 APPROVED → FLAGGED; sem: 33 e 10 | `scoring.py` |
| `k_of_n` | 37 / 26 | com: 14 APPROVED → FLAGGED; sem: 10 | `scoring.py` |

Os demais registros mudam só no texto de `Decision_Reason`. As duas mudanças são as que a auditoria pré-IP aprovou:
- T0 FLAGGED dá `FLAGGED_FINAL` em todas as políticas;
- na `strict`, um bloco rejeitado decide antes de um bloco sinalizado.

Na 3.0.1, a `strict` era mais branda que a `special` quando havia um bloco rejeitado.

O ensaio rodou de novo no desktop em `afee792` e deu os mesmos números: `special` 0, `strict` 60 / 59 e `k_of_n` 37 / 26, todos causados por `scoring.py`.

## 4. Revisão: os achados e o destino de cada um

### 4.1 Primeira rodada, sobre a junção

A revisão leu os arquivos que cada auditoria mudou sem a outra ver, em 5 dimensões:
- cobertura do CHANGELOG;
- correção;
- segurança;
- casos-limite;
- regressões.

Um adjudicador independente tentou refutar cada achado alto, sem receber o raciocínio de quem o levantou.

| # | Sev. | Achado | Destino |
|---|---|---|---|
| 1 | alta | Bloco `Global`/`global` virava bloco de domínio: rejeitava todo artigo ou sobrescrevia a seção global | Corrigido: nome de bloco ignora caixa |
| 2 | alta | `Ctx` e `CTX` se fundiam e um deles perdia os termos | Corrigido: um bloco só, com os termos dos dois e aviso |
| 3 | alta | `strict` e `k_of_n` mudam decisão, e a regressão não cobria | Medido (seção 3.2) e declarado no CHANGELOG |
| 4 | média | Recusa F08 antecipada sem teste em `preview`, `coverage` e ID vazio | Corrigido: testes nos 3 fluxos e nos 2 casos |
| 5 | baixa | Teste do editor de config da TUI usa um validador falso | Registrado: o comportamento foi conferido à mão; falta o teste com o template real |
| 6 | baixa | Metadados de empacotamento, `CITATION.cff` e links do README sem teste | Registrado |
| 7 | baixa | Contagem da suíte no CHANGELOG desatualizada | Corrigido |
| 8 | média | Chave de abreviatura em minúsculas deixava de casar `IoT` | Corrigido: chave em minúsculas casa em qualquer caixa |
| 9 | baixa | Abreviaturas que diferem só na caixa se sobrepunham sem aviso | Corrigido: aviso |
| 10 | baixa | F08 apontava linha errada com abstract de várias linhas | Corrigido: numera registros |
| 11 | baixa | TUI não mostrava os avisos de entrada | Corrigido |
| 12 | baixa | `doctor` culparia a tabela de entrada por um valor ruim do config | Refutado: o config é lido antes; um teste fixa o rótulo certo |
| 13 | média | Texto do corpus começando com `=` virava fórmula no xlsx | Corrigido no xlsx (os dois motores). O CSV é texto puro e fica como está |
| 14 | baixa | O guarda de ReDoS não cobre alternância ambígua (`(a\|a)*`) | Registrado: termos regex vêm de quem escreve a tabela; o guarda cobre quantificador aninhado |
| 15 | baixa | Pacote de apêndice e manifesto com caminho absoluto (usuário do SO) | Corrigido, e também no `protocol.json` |
| 16 | média | `coverage` chamava de morto o termo de bloco pulado pelo fail-fast | Corrigido: a cobertura avalia todos os blocos |
| 17 | média | `MIN_APPROVED_BLOCKS` em texto quebrava todo artigo | Corrigido |
| 18 | média | `"false"` e `"0"` valiam verdadeiro nas flags | Corrigido |
| 19 | média | Sem normalização Unicode: NFD e largura total não casavam | Corrigido: NFKC |
| 20 | média | Run da TUI podia rodar duas vezes e lia widgets fora da thread | Corrigido. A tela de Coverage segue síncrona: não reentra, e mudar exigiria reescrever um teste de fumaça |
| 21 | média | `profile load` sobrescrevia `config.json` | Corrigido: exige `--force` |
| 22 | baixa | Caminho colado com aspas na TUI | Corrigido |
| 23 | baixa | `C#`, `c++` e `.NET` nunca casavam como abreviatura ou variante | Corrigido |
| 24 | baixa | Termo só de curinga casava com tudo | Corrigido: descartado com aviso |
| 25 | baixa | Erro de SO e taxa de erro saíam como traceback na CLI | Corrigido |
| 26 | baixa | Tabela estreita culpava o encoding | Corrigido |
| 27 | baixa | `diff` com ID repetido inventava transições | Corrigido: recusa |
| 28 | média | `doctor` chamava de aviso o que o `run` recusa (título ou resumo ausente) | Corrigido: `doctor` dá erro. A recusa é decisão da auditoria pré-IP |
| 29 | média | Regex antes aceita agora é recusada, inclusive caso não ambíguo | Declarado no CHANGELOG; afinar o guarda fica registrado |
| 30 | média | `TOKEN_UNIT_FOR_GAPS` fora da allowlist voltava a `\S+` em silêncio | Corrigido: aviso no `validate` e no `doctor` |
| 31 | baixa | Níveis padrão e descarte dos positivos do GLOBAL | Declarado no CHANGELOG |
| 32 | baixa | `coverage -o` cria o CSV mesmo vazio | Declarado no CHANGELOG (decisão da auditoria pré-IP) |
| 33 | baixa | Erro por artigo loga WARNING com traceback | Mantido: decisão da auditoria pré-IP (G2). A outra metade, o ID sair sempre como `ERR_`, não procede |

### 4.2 Segunda rodada, sobre o fechamento da primeira

A mesma revisão rodou de novo sobre os arquivos que o fechamento mudou. Ela confirmou 1 alto e levantou 20 médios e baixos. Seis deles eram defeitos das próprias correções da primeira rodada.

| # | Sev. | Achado | Destino |
|---|---|---|---|
| 1 | alta | Caractere de controle (`\x0b`, `\x0c`) num título derrubava o export xlsx depois de todo o corpus processado | Corrigido: vira espaço nas células de texto, nos dois motores |
| 2 | média | A mensagem de "poucas colunas" escondia o erro real de parsing | Corrigido: só sai sem erro de parsing; senão o erro é encadeado |
| 3 | média | Com NFKC na pontuação e não no destaque, um termo pontuava sem aparecer marcado | Corrigido: o destaque procura no NFKC e marca o trecho original |
| 4 | baixa | O protocolo gravava `FAIL_FAST_GLOBAL` cru | Corrigido: grava o booleano usado; protocolo 2.2 |
| 5 | baixa | A grafia do bloco podia vir de uma linha descartada | Corrigido: vem da primeira linha aceita |
| 6 | média | CSV com célula que começa com `=`, `+`, `-` ou `@` | O apóstrofo entrou e saiu na estabilização (4.3), por decisão do usuário: o CSV é o dado cru, e o risco está declarado no CHANGELOG |
| 7 | baixa | O guarda de ReDoS não cobre grupo aninhado nem alternância ambígua | Registrado: termos regex vêm de quem escreve a tabela |
| 8 | média | Uma rodada que falha no meio deixa os artefatos da anterior na pasta | Registrado: comportamento anterior à 3.1.0; usar uma pasta de saída por rodada |
| 9 | média | `ERROR_POLICY` desconhecido desligava o `MAX_ERROR_RATE` | Corrigido: erro de validação |
| 10 | média | Bloco `T0` na tabela colidia com o T0 do GLOBAL | Corrigido: nome reservado, linha recusada |
| 11 | baixa | Nível `inf` derrubava a leitura da tabela | Corrigido: nível inválido |
| 12 | baixa | Erros de `int()`/`float()` em `load_global_params` não nomeiam a chave | Registrado |
| 13 | baixa | `MIN_APPROVED_BLOCKS` acima do número de blocos impede aprovação | Corrigido: aviso no `validate` |
| 14 | baixa | CSV sem proteção de fórmula e nome de aba sem limite | Corrigido o CSV (#6); o nome de aba fica registrado |
| 15 | média | Chaves das regras não passavam por NFKC | Corrigido |
| 16 | baixa | `read_flag` recusa valores que antes passavam | Declarado no CHANGELOG |
| 17 | baixa | `MIN_APPROVED_BLOCKS` 0 ou `true` virou erro | Declarado no CHANGELOG |
| 18 | baixa | Formatos publicados mudaram sem marca de versão | Corrigido: protocolo 2.2 e `manifest_version` 2 |
| 19 | baixa | A CLI escondia o traceback de `NotImplementedError` e `RecursionError` | Corrigido |
| 20 | baixa | O mesmo de #2, visto por outra dimensão | Corrigido com #2 |
| 21 | baixa | `diff` recusava tabelas antigas com vários IDs vazios | A correção estava errada (4.3): o merge pareia vazio com vazio. Na estabilização, ID vazio repetido volta a ser recusado |

### 4.3 Terceira rodada, escalada e estabilização

A terceira rodada confirmou 2 altos, e os dois eram o mesmo defeito: a correção #21 da segunda rodada. Com o ID vazio fora da contagem, o merge externo pareava `''` com `''` e inventava transições. Dos 22 médios e baixos, 11 eram efeitos colaterais da segunda rodada.

Com as 2 iterações de fechamento esgotadas, o portão de escalada foi ao usuário. Ele escolheu estabilizar e fechar: corrigir o alto pelo caminho seguro, aplicar só ajustes pequenos e sólidos, registrar o resto e rodar a verificação uma última vez. Escolheu também que o CSV volte a ser o dado cru.

Aplicado na estabilização:
- `diff`: ID repetido, vazio inclusive, é recusado, e a contagem segue a regra do merge;
- CSV cru (decisão do usuário), com o risco declarado no CHANGELOG;
- a migração para o protocolo 2.2 aplica o significado da 2.2, e não só o rótulo;
- `ERROR_POLICY` é recusado onde é lido;
- `validate` lê `MIN_APPROVED_BLOCKS` com o leitor do motor;
- as chaves de símbolo passam por NFKC em vez de serem descartadas;
- a mensagem de tabela estreita sempre sai e encadeia o erro de parsing;
- o destaque ignora match vazio nos dois caminhos;
- o xlsx limpa U+FFFE, U+FFFF e os nomes de coluna;
- o fonte escreve U+FFFE e U+FFFF como escape;
- os testes da TUI esperam a reabilitação do botão, em vez de uma pausa só.

Registrado, não aplicado:
- markup do Rich e escape de terminal vindos do corpus na saída da CLI;
- bloco da tabela com nome de chave reservada do config (`fields`, `output`, `normalization_rules`);
- hashes do protocolo truncados em 64 bits;
- normalização por cluster no destaque para jamo hangul e vogais índicas de duas partes.

A última rodada da verificação está na seção 4.4.

Cada correção tem pelo menos um teste que reprova quando ela é desfeita. As correções de núcleo das quatro rodadas somam 41 mutações em três baterias: 7 da primeira rodada, 12 também da primeira e 22 da segunda à quarta. As três baterias rodaram de novo em `afee792`, e todas as mutações foram pegas. As correções da CLI e da TUI foram falsificadas do mesmo jeito pelos agentes que as fizeram.

### 4.4 Quarta rodada, a última, sobre a estabilização

Esta é a rodada que o usuário pediu antes do PR. Ela leu os arquivos que a estabilização mudou, nas 5 dimensões. O adjudicador confirmou os 2 altos, que eram um defeito só e vinham da própria estabilização: a troca de "descartar" por "passar por NFKC" nas chaves de símbolo. Os 14 médios e baixos não passaram por adjudicação.

| # | Sev. | Achado | Destino |
|---|---|---|---|
| 1 | alta | Chave de símbolo que o NFKC reescreve virava regra sobre texto comum: `²` -> ` squared` passava a trocar todo dígito `2` do corpus | Corrigido: uma chave de regra que o NFKC reescreve fica de fora, com aviso; a redundante (`ﬁ` -> `fi`) sai sem aviso |
| 2 | alta | O mesmo de #1, visto por outra dimensão | Corrigido com #1 |
| 3 | baixa | A migração para 2.2 põe o rótulo 2.2 num snapshot com flag ilegível e engole o erro | Registrado; declarado no CHANGELOG (Limitações conhecidas) e na `TECHNICAL.md` |
| 4 | baixa | `export_academic_package` empacota um `protocol.json` anterior à 2.2 como está, com os caminhos absolutos dele | Registrado; declarado no CHANGELOG, com o contorno |
| 5 | média | Chaves que o NFKC iguala (`½` e `1⁄2`, `ＭＬ` e `ML`) se sobrepunham sem aviso de duplicata | Corrigido com #1: a chave que o NFKC reescreve fica de fora, e a colisão acaba |
| 6 | média | `MIN_APPROVED_BLOCKS` truncava fração em silêncio (`2.7` virava 2), e infinito quebrava o `validate` | Corrigido: fração e infinito são recusados com o nome da chave |
| 7 | média | `MAX_ERROR_RATE` com `NaN` ou negativo desliga o limite em silêncio, e um valor que não é número falha com erro cru | Registrado; declarado no CHANGELOG |
| 8 | baixa | A limpeza do xlsx quebrava com nomes de coluna repetidos, inclusive os que ela mesma iguala | Corrigido: percorre as colunas por posição |
| 9 | baixa | xlsx: célula acima de 32 767 caracteres truncada em silêncio, e nome de aba inválido que só falha depois do processamento | Registrado; declarado no CHANGELOG |
| 10 | baixa | O NFKC por cluster do destaque difere do NFKC do texto inteiro quando a composição atravessa clusters | Registrado: é o item de cluster da seção 4.3 |
| 11 | baixa | Migração: caminho sem componente final vira nome vazio, e flag ilegível fica como estava | Registrado; declarado na `TECHNICAL.md` |
| 12 | média | `ERROR_POLICY` recusado em `load_global_params` faz falhar um config que rodava | Declarado no CHANGELOG desde a estabilização |
| 13 | baixa | `validate_protocol_snapshot` recusa snapshot 2.1, e a `TECHNICAL.md` ainda descrevia a 2.1 | Corrigido na documentação: a `TECHNICAL.md` descreve a 2.2 e a migração. A recusa da 2.1 pelo validador é o desenho, porque a 2.1 passa pela migração |
| 14 | baixa | `diff` trata NaN e vazio como o mesmo ID, e a mensagem de ID repetido mudou de formato | Declarado no CHANGELOG |
| 15 | baixa | A grafia do bloco vem da primeira linha aceita, o que pode mudar o nome do bloco na saída | Declarado no CHANGELOG |
| 16 | baixa | Bloco `T0` da tabela é descartado com aviso, o que muda o resultado de quem o usava | Declarado no CHANGELOG desde a estabilização |

As correções de #1, #5, #6 e #8 estão em `afee792`. As regras de ligadura da RSL1 são redundantes com o NFKC, e o teste da 3.0.1 que exige zero avisos na tabela histórica continua verde. A regressão oficial em `afee792` dá 0 registros mudados na RSL1 e no piloto da RSL2 (seção 3.1).

## 5. Eficiência

Medido no desktop (Python 3.12, ambiente do `uv.lock`), melhor de 3 rodadas, com `config_v8.json`:

| Versão | 505 registros | 5 050 registros (10 cópias) | ms por registro (5 050) |
|---|---|---|---|
| 3.0.1 | 12,4 s | 94,5 s | 18,7 |
| 3.1.0 | 10,1 s | 96,5 s | 19,1 |

A diferença está no ruído, e o tempo cresce linearmente: cerca de 6 minutos para 20 000 registros.

O perfil mostra que 47% do tempo vai para `io.highlight_text`. Ela gera as colunas `*_Highlighted` e não entra em decisão nenhuma. Otimizá-la antes de travar mudaria código sem ganho para a triagem e pediria nova regressão, então ela fica como candidata à 3.2.

## 6. Como travar

1. Fazer o merge do PR.
2. Apagar a tag local `v3.1.0` do desktop, que aponta para o commit de junho, antes de criar a tag da versão.
3. Criar a release `v3.1.0` no GitHub. O workflow publica no PyPI e confere a tag contra a versão.
4. Na RSL1 e na RSL2, fixar `fastslr==3.1.0` e guardar o `protocol.json` de cada rodada, que traz `triage_version` e os hashes do corpus, dos termos e do config.

## 7. Reprodução

```
python docs/regressao_v3.0.1/prepare_inputs.py <Final_Corpus.csv> <inputs>
python docs/regressao_v3.1.0/prepare_sources.py <repo> <fontes> --base 4a66697 --merged <ref>
python docs/regressao_v3.1.0/run_all.py <fontes> <inputs> tests/fixtures/historical/config_v8.json tests/fixtures/historical/terms_final.csv <out>
python docs/regressao_v3.1.0/compare.py <out> <relatorio> --reference <rodadas de 2026-10-10>
```

Para outra política, copie o `config_v8.json` mudando só a `DECISION_POLICY`. Para outro corpus, use `run_all.py --variant NOME=ARQUIVO` e `compare.py --variants NOME --rows N`.
