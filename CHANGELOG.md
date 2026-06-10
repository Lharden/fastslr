# Changelog

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [3.1.0] - 2026-06-10

Bateria final de auditoria profunda pré-registro de propriedade intelectual:
58 findings levantados por 9 dimensões de análise, verificação adversarial,
28 correções aprovadas item a item + revisão de qualidade da execução (G4).

### Adicionado

- Guard-rails de decisão: T0 FLAGGED resulta em `FLAGGED_FINAL` em todas as
  políticas (`special`, `strict`, `k_of_n`), sem superar bloco REJECTED.
- Validação de configuração centralizada no *controller*: CLI, TUI, `preview`
  e `coverage` bloqueiam configs inválidas e colunas obrigatórias não resolvidas.
- Detecção de encoding UTF-16 (BOM/NUL) e respeito ao encoding configurado.
- Normalização de markup/entidades HTML conhecidos em abstracts.
- Aviso de IDs duplicados no corpus (sem deduplicar).
- Proteção contra ReDoS em regex de termos (`is_regex`) e `TOKEN_UNIT_FOR_GAPS`
  (allowlist), incluindo quantificadores de intervalo aninhados (`(a{2,})+`).
- Corpus vazio (0 linhas) aborta `run`, `preview` e `coverage` com erro claro.
- Smoke tests da TUI (+24 testes) e regressões da auditoria (suite 218 → 293).
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

### Alterado

- `build-system` exige `setuptools>=77.0.3` (suporte a licença PEP 639).
- README com links absolutos (renderização correta na página do PyPI).

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

[3.0.0]: https://github.com/Lharden/fastslr/releases/tag/v3.0.0
