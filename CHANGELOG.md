# Changelog

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

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
