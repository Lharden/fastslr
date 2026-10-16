# Changelog

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Unreleased]

### Corrigido

- O README, o Guia do Usuário e o `docs/TECHNICAL.md` ainda citavam a 3.0.1, e o
  `CITATION.cff` trazia a data da auditoria local de junho. Inclui o modelo de
  texto para a seção de métodos do artigo. Na página da 3.1.0 no PyPI, a
  descrição, que é o README, começa com "FastSLR v3.0.1", mas o pacote é o da
  3.1.0. Um teste agora amarra essas versões e a data do `CITATION.cff` à
  `VERSION` e ao CHANGELOG.
- O workflow de publicação lê a versão sem importar o pacote. A primeira
  execução da release v3.1.0 falhou por isso, sem publicar nada.

## [3.1.0] - 2026-10-15

Junta a bateria final de auditoria pré-registro de propriedade intelectual
(feita em 2026-06-10 sobre a 3.0.0 e nunca publicada) à 3.0.1: 58 findings
levantados por 9 dimensões de análise, verificação adversarial, 28 correções
aprovadas item a item + revisão de qualidade da execução (G4). Onde as duas
auditorias decidiram o mesmo ponto, vale a decisão da 3.0.1. A junção passou por
quatro rodadas de revisão multidimensional com adjudicação adversarial, cujos
achados estão corrigidos aqui ou declarados abaixo, e por regressão nos 505 registros históricos da RSL1: nenhuma
célula muda com a política `special`. Revisão, regressão e o destino de cada
achado: [`docs/REVISAO_v3.1.0.md`](docs/REVISAO_v3.1.0.md).

### Quebras de comportamento

Nenhuma muda a triagem da RSL1 (`config_v8.json`, `terms_final.csv`, política
`special`). Quem usa outra configuração deve ler esta lista antes de travar.

- **Políticas `strict` e `k_of_n`**: T0 FLAGGED passa a dar `FLAGGED_FINAL`, e na
  `strict` um bloco REJECTED passa a dar `REJECTED_FINAL` (antes, REJECTED com
  FLAGGED dava FLAGGED). Nos 505 históricos com essas políticas mudam 37 decisões
  na `strict` e 14 na `k_of_n` (com palavras-chave), todas causadas por
  `scoring.py`.
- Corpus sem coluna de título ou de resumo é recusado por `run`, `preview`,
  `coverage` e `doctor`. Antes, o texto ausente valia vazio.
- Regex de termo com quantificador variável dentro de grupo repetido (`(\w+\s)*`)
  é recusada com aviso, inclusive casos não ambíguos como `(\d{1,3},)+`.
- `TOKEN_UNIT_FOR_GAPS` aceita só `\S+` e `\w+`; outro valor volta a `\S+`, com
  aviso no `validate` e no `doctor`.
- Termos positivos do bloco GLOBAL são descartados com aviso: eles nunca
  afetaram o T0.
- Sem `PONTUACAO_NIVEIS`, os níveis válidos são os padrões (1 a 5); um termo de
  nível fora deles pontua 0, com aviso.
- O nome de bloco na tabela de termos ignora caixa: `Global` é o GLOBAL, e `Ctx`
  e `CTX` são um bloco só, com os termos dos dois.
- Chave de abreviatura toda em minúsculas casa em qualquer caixa (`iot` expande
  `IoT`); chave com maiúscula guarda a caixa, como no F04.
- Texto e termos passam por NFKC antes das regras.
- Termo feito só de curinga (`*`, `**`) é descartado com aviso.
- `protocol.json` passa à versão 2.2 (a 2.1 continua migrável): grava nome de
  arquivo em vez de caminho, e as flags com o valor que o motor usou. O
  `appendix_manifest.json` do pacote (`manifest_version` 2) grava o SHA-256 de
  cada arquivo.
- O xlsx de resultados nunca grava fórmula, e caracteres que uma célula não
  aceita (`\x0b`, `\x0c`, U+FFFE, U+FFFF) viram espaço, nas células e nos nomes
  de coluna.
- O CSV de resultados é o dado cru, célula a célula, por decisão do mantenedor:
  ele volta inteiro pelo `diff`. Um título que começa com `=`, `+`, `-` ou `@`
  pode ser executado como fórmula se o CSV for aberto direto numa planilha.
  Importe o CSV como texto, ou use o xlsx, que é o arquivo dos revisores. O CSV
  vem desligado por padrão.
- O destaque (`*_Highlighted`) procura no texto em NFKC, como a pontuação, e
  marca o trecho original.
- Um bloco chamado `T0` na tabela de termos é recusado: o nome é do bloco que
  vem do GLOBAL.
- `ERROR_POLICY` diferente de `flag` e `fail` (inclusive `FLAG`) é recusado ao
  ler o config, e o `validate` aponta: antes, desligava em silêncio o limite
  `MAX_ERROR_RATE`.
- `diff` recusa ID repetido nos resultados, inclusive ID vazio repetido.
- Uma chave de regra de normalização (abreviatura, variante ou símbolo) que o
  NFKC reescreve fica de fora, com aviso: ela não casaria como está escrita,
  porque o texto já é lido em NFKC. A regra `²` -> ` squared` não vira mais uma
  regra sobre todo dígito `2`. A chave redundante, que só diz o que o NFKC já faz
  (`ﬁ` -> `fi`), sai sem aviso.
- Flag booleana com valor ilegível (`null`, `""`, `2`) e `MIN_APPROVED_BLOCKS`
  menor que 1, fracionário (`2.7`) ou infinito são recusados com o nome da chave.
- `diff` trata ID ausente (NaN) e ID vazio como o mesmo ID, e a mensagem de ID
  repetido mudou de formato.
- A grafia de um bloco na saída vem da primeira linha aceita da tabela de termos,
  o que pode mudar o nome do bloco quando a primeira linha era descartada.
- `fastslr profile load` não sobrescreve um `config.json` existente sem `--force`.

### Adicionado

- Guard-rails de decisão: T0 FLAGGED resulta em `FLAGGED_FINAL` em todas as
  políticas (`special`, `strict`, `k_of_n`), sem superar bloco REJECTED.
- Validação de configuração centralizada no *controller*: CLI, TUI, `preview`
  e `coverage` bloqueiam configs inválidas e colunas obrigatórias não resolvidas.
- Detecção de encoding UTF-16 (BOM/NUL) e respeito ao encoding configurado.
- Normalização de markup/entidades HTML conhecidos em abstracts (`&amp;`,
  `<sub>`, `<sup>`, `<inf>`), antes das regras da 3.0.1.
- A recusa de ID vazio ou repetido (F08) acontece também na checagem que roda
  antes de qualquer artefato: `run`, `preview` e `coverage` param sem criar a
  pasta de saída. A auditoria pré-IP só avisava, e o aviso saiu.
- Proteção contra ReDoS em regex de termos (`is_regex`) e `TOKEN_UNIT_FOR_GAPS`
  (allowlist), incluindo quantificadores de intervalo aninhados (`(a{2,})+`).
- Corpus vazio (0 linhas) aborta `run`, `preview` e `coverage` com erro claro.
- Smoke tests da TUI (+24 testes), regressões da auditoria pré-IP e da revisão
  da junção: a suíte da 3.1.0 coleta 459 testes, e 2 deles pulam quando
  `data/terms_final.csv`, que não é versionado, está ausente.
- Instrumento da regressão em `docs/regressao_v3.1.0/`: base, junção e uma árvore
  por módulo desfeito, com atribuição de causa por leave-one-out.
- Metadados de empacotamento: `authors`/`maintainers`, `keywords`, `classifiers`,
  `[project.urls]`, `CITATION.cff` e licença em expressão SPDX (PEP 639).

### Corrigido

- Mensagens de erro do *controller* internacionalizadas (en/pt_BR/es) — corpus
  vazio, diff sem ID comum, export inválido e projeto existente.
- Executável instalado (`fastslr`) usa o handler global de erros amigável.
- Spinner com frames ASCII (não quebra em stdout redirecionado no Windows cp1252).
- Editor de config da TUI aceita o template canônico gerado pelo próprio produto.
- `coverage -o` sempre cria o CSV (com cabeçalho) mesmo sem termos cobertos.
- Comando `terms` exibe os avisos de parse propagados.
- Sdist inclui `conftest.py` (suite roda completa a partir do sdist).
- Workflow de publicação valida tag vs versão e protege execução manual.
- Flags booleanas escritas como texto (`"false"`, `"0"`) valem o que dizem; valor
  ilegível é recusado com o nome da chave. `MIN_APPROVED_BLOCKS` é inteiro >= 1.
- O xlsx grava todo texto como texto: título que começa com `=` não vira
  fórmula viva na planilha dos revisores.
- `diff` recusa ID repetido, vazio inclusive, em vez de parear cada cópia com
  cada cópia e inventar transições.
- `coverage` avalia todos os blocos de todos os artigos: termo de bloco pulado
  pelo fail-fast ou pelo T0 não aparece mais como morto.
- Abreviatura e variante com borda não alfanumérica (`C#`, `.NET`, `c++`) casam.
- Regras de abreviatura que diferem só na caixa geram aviso.
- F08 numera os registros a partir de 1, não por linha do arquivo.
- Tabela com colunas de menos diz isso, em vez de culpar o encoding.
- CLI: erro de permissão (planilha aberta no Excel), outros erros de SO e
  `RuntimeError` (taxa de erro) saem como mensagem, com código 1, sem traceback.
- TUI: o resumo do Run mostra os avisos de entrada; o Run não roda duas vezes com
  duplo clique; caminho colado com aspas funciona em todas as telas.
- Um caractere de controle num título não derruba mais o export xlsx depois de
  todo o corpus processado.
- Um termo que pontua aparece destacado também em texto NFD ou de largura total.
- Tabela de entrada estreita e linha malformada: a mensagem traz a contagem de
  colunas e, quando houve, o erro de parsing encadeado; um não esconde o outro.
- Nível `inf` ou `1e400` na tabela de termos é nível inválido, não um
  `OverflowError`; a grafia de um bloco vem da primeira linha aceita.
- `validate` avisa quando `MIN_APPROVED_BLOCKS` passa do número de blocos (nenhum
  artigo seria aprovado), lendo o valor como o motor lê (`"5"`, `5.0`).
- CLI: `NotImplementedError` e `RecursionError` mantêm o traceback, porque são bug.
- Protocolo de versão anterior migrado para 2.2 recebe o significado da 2.2
  (nomes de arquivo e flags booleanas), não só o rótulo.
- A limpeza do xlsx percorre as colunas por posição: nomes de coluna repetidos,
  inclusive os que a própria limpeza iguala, não derrubam mais o export.

### Alterado

- `build-system` exige `setuptools>=77.0.3` (suporte a licença PEP 639).
- README com links absolutos (renderização correta na página do PyPI).
- `docs/TECHNICAL.md` descreve o protocolo 2.2.

### Limitações conhecidas

Achados da revisão que ficam para depois da 3.1.0. Nenhum muda a triagem da
RSL1. A lista completa, com o destino de cada um, está em
[`docs/REVISAO_v3.1.0.md`](docs/REVISAO_v3.1.0.md).

- `MAX_ERROR_RATE` com `NaN` ou valor negativo desliga o limite de taxa de erro
  em silêncio, e um valor que não é número falha com erro cru.
- xlsx: célula com mais de 32 767 caracteres é truncada em silêncio, e um nome
  de aba inválido só falha depois do processamento.
- `export_academic_package` empacota um `protocol.json` anterior à 2.2 como
  está, e os caminhos absolutos dele (com o usuário do SO) podem chegar ao pacote
  publicado. Para empacotar uma rodada antiga, refaça a rodada na 3.1.0 ou
  migre o arquivo com `fastslr.core.io.migrate_protocol_snapshot`.
- A migração para 2.2 deixa como estava uma flag ilegível do snapshot antigo.

## [3.0.1] - 2026-10-10

Correções da auditoria pré-congelamento da v3.0.0 (2026-10-10), achados F01–F10.
Os defeitos de normalização rejeitavam registros elegíveis. A regressão nos 505
registros históricos, com a causa de cada diferença, está em
[`docs/REGRESSAO_v3.0.1.md`](docs/REGRESSAO_v3.0.1.md).

### Corrigido

- **F01** — Símbolo que vale uma palavra (`&` → `and`, `/` → `or`, `+` → `and`,
  `w/` → `with`) vira a palavra entre espaços: "oil&gas" → "oil and gas" e
  "AI/ML" → "artificial intelligence or machine learning" (antes, texto colado:
  "oilandgas", "intelligenceormachine"). O alvo de `symbol_replacement` guarda os
  espaços escritos na lista. Siglas como `O&G` e `E&P` casam como frase exata;
  componente de uma letra não gera proximidade.
- **F02** — Hífen entre caracteres de palavra vale espaço, no texto e nos termos:
  "machine-learning" casa `machine learning`. Variantes compostas com hífen
  (`e-procurement`, `well-bore`) continuam aplicadas. Termo regex com hífen entre
  letras gera aviso, porque não casaria mais.
- **F03** — O separador da proximidade passa de `[\s\-/.,]+` para `[\s\-/]+`: a
  proximidade não atravessa ponto nem vírgula ("engine oil. Gas turbines",
  "food, oil, natural gas"). "oil-and-gas" continua casando.
- **F04** — Expansão de abreviatura sensível à caixa: casa a sigla como escrita e
  em maiúsculas (`ML` expande; "5 ml" não). A chave da regra guarda a caixa.
- **F05** — `source_row` (e o `row=` de `Highlights_*`, `AntiHighlights_*`,
  `Flags_*`) é a linha do arquivo de termos, como nos avisos: "oil and gas" em
  `terms_final.csv` sai como linha 53, não 51.
- **F06** — Termo regex não gera proximidade; `*` num componente da proximidade é
  curinga, não asterisco literal.
- **F07** — No mapeamento automático do ID, `UT` vem antes de `ID`: no Web of
  Science, `ID` são as palavras-chave Keywords Plus.
- **F08** — Entrada com ID de registro vazio ou repetido, ou sem coluna de ID, é
  recusada: `run` sai com código 1 e mensagem com as linhas; `doctor` reporta erro.
- **F09** — Falta da coluna de palavras-chave gera aviso no terminal, no `doctor`,
  em `triage_report.txt` e em `protocol.json` (`processing.input_warnings`), porque
  o uplift passa a valer para todos os registros.
- **F10** — `xlsxwriter` passa a ser dependência declarada (o `config` histórico o
  pede); `uv.lock` trava o ambiente.

### Alterado

- Testes que fixavam o comportamento defeituoso foram atualizados (abreviatura
  sem distinção de caixa, `cplusplus` colado, vírgula como separador).

## [3.0.0] - 2026-05-30

Reescrita completa do FastSLR como ferramenta universal e 100% determinística
(sem IA/ML) para triagem de Revisões Sistemáticas de Literatura, distribuída via
PyPI (`pip install fastslr`).

### Adicionado

- Interface de linha de comando (CLI) baseada em [Typer](https://typer.tiangolo.com/),
  com os comandos: `run`, `doctor`, `preview`, `coverage`, `diff`, `new-project`,
  `export`, `terms`, `profile`, `tui` e `version`.
- Camada *controller* que oferece um caminho programático simplificado para uso
  do FastSLR como biblioteca.
- Internacionalização (i18n) por meio de arquivos de *locale* em JSON, com suporte
  a inglês (`en`), português do Brasil (`pt_BR`) e espanhol (`es`).
- Interface interativa de terminal (TUI) construída com [Textual](https://textual.textualize.io/),
  composta por 10 telas.
- Pacote acadêmico para reprodutibilidade total, com `protocol.json` e hashes
  SHA-256 dos artefatos gerados.
- Conjunto de 21 validações para o arquivo `terms.csv`, com confirmação interativa.
- Marcador `py.typed`, exportando a tipagem do pacote para consumidores externos.
- Licença MIT.
- Publicação no PyPI via *Trusted Publishing* (OIDC), sem token armazenado.
- Suíte de testes de regressão e *hardening* derivada de testes de estresse.

### Alterado

- Reestruturação do projeto de v2 para v3: o repositório foi achatado para um
  pacote instalável via pip, adotando o *layout* `src/`.
- Documentação revisada com guia do usuário e documento de arquitetura técnica;
  `pip install fastslr` passa a ser o método de instalação primário.
- Auditoria completa do código-base, com 46 *findings* corrigidos (Fases 0 a 5).

### Removido

- Todos os componentes de IA/ML: o FastSLR v3.0.0 é uma ferramenta totalmente
  determinística, sem qualquer dependência de inteligência artificial.
- Código morto identificado durante a auditoria e a limpeza de pré-publicação.

[3.0.1]: https://github.com/Lharden/fastslr/releases/tag/v3.0.1
[3.0.0]: https://github.com/Lharden/fastslr/releases/tag/v3.0.0
