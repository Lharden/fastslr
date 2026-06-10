# Changelog

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

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
