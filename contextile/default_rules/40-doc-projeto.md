---
apply: manually
---

# Documentação — Repositório e Projeto

> **Aplica-se quando**: criando ou atualizando README, CHANGELOG, CONTRIBUTING; escrevendo mensagens de commit; ou estruturando documentação no nível do repositório.
>
> Para decisões arquiteturais, diagramas e runbooks, ver `41-doc-arquitetura.md`. Para docstrings em código Python, ver `11-python-estilo.md`.

## README — o contrato com o leitor

Todo repositório deve ter um README que responda, **nessa ordem**:

1. **O que é** — uma ou duas frases. Ex: "Serviço HTTP para gestão de pedidos."
2. **Para quem** — usuários esperados (devs internos, clientes, integradores).
3. **Como rodar local** — 3-5 comandos do `git clone` ao app rodando.
4. **Como rodar testes/lint** — um comando.
5. **Links** — documentação detalhada, deploy, dashboards.

A primeira tela vale ouro. Quem chega pelo GitHub lê só os primeiros parágrafos.

### Estrutura recomendada

```markdown
# Nome do Projeto

Descrição em 1-2 frases. O que é, para quem.

## Pré-requisitos

- Python 3.12+
- Postgres 16+
- uv

## Instalação

```bash
git clone git@github.com:org/projeto.git
cd projeto
uv sync
cp .env.example .env  # edite com seus valores
```

## Uso

```bash
uv run uvicorn meu_app.api.app:create_app --reload --factory
```

API em <http://localhost:8000>, docs em <http://localhost:8000/docs>.

## Desenvolvimento

```bash
uv run pytest                  # testes
uv run ruff check              # lint
uv run ruff format             # formatar
uv run mypy src                # type check
```

## Documentação

- [Arquitetura](docs/arquitetura/visao-geral.md)
- [ADRs](docs/adr/)
- [Runbooks](docs/runbooks/)
- [API](https://docs.example.com)

## Licença

MIT (ou Proprietary, conforme o caso).
```

### Princípios do README

- **Comandos copiáveis** — não exija que o leitor adapte o snippet.
- **Atualizado** — exemplo que não funciona é pior que ausência de exemplo.
- **Conciso** — sumarize, linke o detalhe. Walls of text afogam o essencial.
- **Verificável em CI** quando possível — testar que os comandos do README funcionam pega regressões.

### O que NÃO vai no README

- **Histórico de versões** — vai no CHANGELOG.
- **Decisões de design profundas** — vão em ADRs.
- **Tutoriais longos ou guias** — vão em `docs/`.
- **Referência completa de API** — vai em docs gerados (OpenAPI/mkdocs).
- **Notas de troubleshooting** — vão em runbooks.

## CHANGELOG — formato Keep a Changelog

Use o formato [Keep a Changelog](https://keepachangelog.com), em `CHANGELOG.md` na raiz:

```markdown
# Changelog

Todas as mudanças relevantes deste projeto serão documentadas aqui.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e este projeto adere a [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [Unreleased]

### Added
- Endpoint `POST /v1/pedidos/em-massa` para criação em lote.

### Fixed
- Corrigido N+1 ao listar clientes com pedidos.

## [1.2.0] - 2026-04-15

### Added
- Paginação keyset em `GET /v1/pedidos`.

### Changed
- `POST /v1/clientes` agora rejeita campos extras (era ignorado).

### Deprecated
- `GET /v1/pedidos?offset=N` — usar `?cursor=...` em vez. Será removido em 2.0.

### Removed
- Endpoint `GET /v1/legacy/*` (deprecated desde 1.0).

### Fixed
- Race condition no cálculo de saldo em transferências concorrentes.

### Security
- Atualização do `cryptography` para corrigir CVE-2026-XXXX.
```

### Categorias (use sempre as mesmas)

**Added, Changed, Deprecated, Removed, Fixed, Security.** Não invente categorias adicionais (`Refactor`, `Tests`) — refactors invisíveis ao usuário não vão no CHANGELOG. O CHANGELOG é para **mudanças observáveis** por quem consome.

### Versionamento — SemVer

Use **SemVer** (`MAJOR.MINOR.PATCH`):

- **MAJOR**: breaking changes (campo removido, comportamento mudou).
- **MINOR**: features novas, retrocompatíveis.
- **PATCH**: bug fixes sem mudança de contrato.

Pre-releases: `1.2.0-rc.1`, `1.2.0-beta.2`.

### Quando atualizar

**Junto com o PR** que faz a mudança. Reviewer cobra. PR sem entrada no CHANGELOG quando aplicável é incompleto.

A seção `[Unreleased]` acumula mudanças até a release. No momento da tag, vira `[X.Y.Z] - YYYY-MM-DD` e abre uma nova `[Unreleased]`.

## CONTRIBUTING — quando criar

Crie quando:

- Repo é open-source ou tem contribuidores externos.
- Existem convenções não óbvias (branch naming, processo de PR, definition of done).

Conteúdo mínimo:

- Como rodar testes/lint.
- Como abrir issue (template, label conventions).
- Convenções de commit e branch.
- Processo de review (quantos approves, quem revisa).
- Definition of Done (testes, CHANGELOG, docs atualizadas).
- Link para Code of Conduct.

Em **repo interno pequeno**, o próprio README pode absorver o CONTRIBUTING.

## Mensagens de commit — Conventional Commits

Recomendação: [Conventional Commits](https://www.conventionalcommits.org).

```
<tipo>(<escopo opcional>): <descrição imperativa curta>

[corpo opcional explicando o porquê]

[rodapé opcional: BREAKING CHANGE, refs #issue]
```

### Tipos comuns

| Tipo       | Uso                                                          |
| ---------- | ------------------------------------------------------------ |
| `feat`     | Nova feature visível ao usuário (entra como `Added` no CHANGELOG). |
| `fix`      | Correção de bug (`Fixed`).                                   |
| `docs`     | Apenas documentação.                                         |
| `refactor` | Mudança sem alterar comportamento externo.                   |
| `perf`     | Melhoria de performance (sem mudar contrato).                |
| `test`     | Apenas testes.                                               |
| `chore`    | Manutenção (deps, lint, configs).                            |
| `build`    | Sistema de build, packaging.                                 |
| `ci`       | Pipelines, GitHub Actions.                                   |

### Exemplos bons

```
feat(pedidos): adiciona criação em massa via POST /v1/pedidos/em-massa
fix(cliente): corrige N+1 ao carregar pedidos
refactor(infra): extrai PedidoRepository para módulo próprio
docs(readme): atualiza instruções de setup com uv
perf(consulta): substitui offset por keyset pagination em /v1/pedidos
```

### Exemplos ruins

```
update                          # diz nada
fix stuff                       # diz nada
wip                             # commit incompleto não vai pra main
asdfasdf                        # ¯\_(ツ)_/¯
"corrigido bug"                 # aspas, vago, sem escopo
```

### Breaking changes

Anuncie no rodapé:

```
feat(api): muda formato do response de /v1/pedidos

BREAKING CHANGE: o campo `total` agora é string (Decimal serializado),
era number. Clientes precisam parsear como string.

Refs: #1234
```

### Benefícios

- **CHANGELOG automático** via `git-cliff`, `semantic-release`, ou similar.
- **Versioning automático** baseado em tipos (`feat` → minor, `fix` → patch, `BREAKING CHANGE` → major).
- **Histórico legível** em `git log --oneline`.

Mesmo sem automação, vale como **convenção de clareza**.

## LICENSE

Sempre tenha um arquivo `LICENSE` na raiz. Sem ele, o código é **All Rights Reserved** por padrão — ninguém pode usar legalmente.

Para projetos internos/proprietários, um `LICENSE` claro evita confusão se o repo for compartilhado ou herdado.

## Documentação envelhece — defesas

Documentação **fora do código** (README, runbooks) envelhece. Defesas:

- **Atualize no mesmo PR** que muda o comportamento. Sem exceção.
- **Revise periodicamente** — toda sprint de tech debt inclui passar olhos.
- **Testes para exemplos do README** quando possível — comando do README quebra build se ficou desatualizado.
- **Datas em runbooks/docs** ajudam a julgar relevância na hora da leitura.

## Anti-padrões

- ❌ README ausente ou de uma linha em projeto não-trivial.
- ❌ "TODO: documentar" deixado mergado no README.
- ❌ CHANGELOG sem datas, versões, ou categorias padronizadas.
- ❌ Mudanças relevantes ao usuário mergadas sem entrada no CHANGELOG.
- ❌ Mensagens de commit `wip`, `fix stuff`, `update`, `asdf`.
- ❌ Comandos no README que não funcionam mais.
- ❌ Documentação detalhada inline no README quando deveria estar em `docs/`.
- ❌ Múltiplos arquivos contradizendo (README diz X, `docs/install.md` diz Y).
- ❌ Documentar comportamento que **ainda não existe** (wishful documentation).
- ❌ Sem `LICENSE` em repo público — código fica em limbo legal.
- ❌ "Refactor" ou "Tests" no CHANGELOG (não é mudança observável pelo usuário).
- ❌ CHANGELOG editado fora de PR — perde o link com a mudança.
