---
apply: by model decision
instructions: Apply when setting up a new Python project, configuring pyproject.toml, managing dependencies with uv, or organizing project folder structure.
---

# Python — Estrutura de Projeto

> **Aplica-se quando**: criando projeto Python do zero, configurando `pyproject.toml`, gerenciando dependências, ou organizando layout de pastas.

## Layout `src/`

Use o **layout `src/`** como padrão:

```
projeto/
├── src/
│   └── meu_app/
│       ├── __init__.py
│       ├── dominio/
│       ├── aplicacao/
│       ├── infra/
│       └── api/
├── tests/
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── pyproject.toml
├── uv.lock
├── .python-version
├── .env.example
├── .gitignore
└── README.md
```

### Por que `src/`

1. **Força instalação** do pacote para importar — evita "funciona porque está no cwd" que quebra em produção.
2. **Separa código de configuração** (root tem só metadados; código vive isolado).
3. **Testes importam do pacote instalado**, não de arquivos relativos — pega bugs de packaging cedo.

### Estrutura interna por camada

Organize por **camada e domínio**, não por tipo (não use `models/`, `services/`, `helpers/`):

```
src/meu_app/
├── dominio/              # entidades, value objects, regras de negócio puras
│   ├── pedido.py
│   └── cliente.py
├── aplicacao/            # casos de uso, orquestração
│   ├── checkout.py
│   └── relatorios.py
├── infra/                # adaptadores: DB, HTTP externo, fila
│   ├── db.py
│   ├── pagamento_gateway.py
│   └── repositorios/
└── api/                  # entrada HTTP, CLI, workers
    ├── routers/
    └── schemas/
```

Dependências apontam **de fora para dentro**: `api` → `aplicacao` → `dominio`. `dominio` não importa de ninguém. `infra` implementa interfaces declaradas em `dominio`/`aplicacao`.

## `pyproject.toml` como fonte única

Tudo (metadados, deps, configs de ferramentas) vive aqui. **Não** use `setup.py`, `setup.cfg`, `requirements.txt`.

Esqueleto mínimo:

```toml
[project]
name = "meu-app"
version = "0.1.0"
description = "Descrição curta do projeto."
readme = "README.md"
requires-python = ">=3.12"
authors = [{name = "Time", email = "time@empresa.com"}]
license = {text = "Proprietary"}

dependencies = [
    "fastapi>=0.115,<0.116",
    "pydantic>=2.7,<3",
    "pydantic-settings>=2.3,<3",
    "sqlalchemy>=2.0,<3",
]

[project.scripts]
meu-app = "meu_app.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/meu_app"]
```

## Dependências de desenvolvimento — PEP 735

Use `[dependency-groups]` (PEP 735, suportado por uv):

```toml
[dependency-groups]
dev = [
    "ruff>=0.6",
    "mypy>=1.11",
    "pre-commit>=3.7",
]
test = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "pytest-mock>=3.14",
]
```

Instala com `uv sync --group dev --group test` ou `uv sync --all-groups`.

> **Legado**: se a versão do uv ainda não suporta `dependency-groups`, use `[project.optional-dependencies]` com a mesma estrutura. Migre quando possível.

## Pinning de versões

Para **bibliotecas** publicadas: ranges permissivos (`fastapi>=0.115,<0.116`).
Para **aplicações**: ranges no `pyproject.toml` + lock estrito em `uv.lock` (commitado).

Regras:

- **Pin major**: `pacote>=X,<X+1` — protege de breaking changes.
- **Pin minor** somente se há motivo documentado (bug conhecido, API instável).
- **`uv.lock`** commitado garante reproducibilidade exata em build/deploy.

## `uv` como gerenciador

Comandos essenciais:

```bash
uv init                            # cria pyproject.toml + estrutura
uv add fastapi sqlalchemy          # adiciona dep ao pyproject.toml + uv.lock
uv add --group dev ruff mypy       # dep de grupo
uv remove pacote                   # remove
uv sync                            # instala tudo do lock
uv sync --all-groups               # inclui grupos opcionais
uv run python -m meu_app           # roda dentro do venv automático
uv run pytest                      # idem
uv lock --upgrade                  # atualiza lock para versões mais novas dentro dos ranges
uv lock --upgrade-package fastapi  # atualiza um pacote específico
```

Não use `pip install` direto — quebra o lock. Tudo passa por `uv`.

## Python pin

`.python-version` na raiz do projeto:

```
3.12
```

`uv` lê isso e instala/usa a versão certa automaticamente (`uv python install` instala se faltar).

## Variáveis de ambiente

### `.env` (NÃO commitar)

```
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dev
REDIS_URL=redis://localhost:6379
LOG_LEVEL=DEBUG
DEBUG=true
```

### `.env.example` (commitar)

```
DATABASE_URL=postgresql+asyncpg://user:pass@host/db
REDIS_URL=redis://host:6379
LOG_LEVEL=INFO
DEBUG=false
```

Mantenha `.env.example` atualizado — ele documenta as variáveis necessárias.

### Carregamento

Use `pydantic_settings.BaseSettings` (ver regra `17-python-modelagem.md`). Não use `os.getenv` espalhado pelo código — config tem que ser **validada no startup**.

## `.gitignore` essencial

```
__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/
.mypy_cache/
.coverage
htmlcov/
.venv/
venv/
.env
*.egg-info/
dist/
build/
.idea/
.vscode/
```

## Configurações de ferramentas em `pyproject.toml`

Centralize tudo:

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "SIM", "RUF"]

[tool.ruff.format]
quote-style = "double"

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_ignores = true

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
asyncio_mode = "auto"
markers = [
    "slow: testes lentos",
    "integration: requer serviços externos",
    "e2e: ponta a ponta",
]
```

## Entrypoints

### CLI (`[project.scripts]`)

```toml
[project.scripts]
meu-app = "meu_app.cli:main"
```

Disponível como comando `meu-app` após `uv sync`.

### Módulo executável (`__main__.py`)

```python
# src/meu_app/__main__.py
from meu_app.cli import main

if __name__ == "__main__":
    main()
```

Permite `python -m meu_app` ou `uv run python -m meu_app`.

## Pre-commit (recomendado)

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: local
    hooks:
      - id: mypy
        name: mypy
        entry: uv run mypy src
        language: system
        pass_filenames: false
```

`uv run pre-commit install` na primeira clonagem do repo.

## Anti-padrões

- ❌ `setup.py` ou `requirements.txt` em projeto novo.
- ❌ `pip install` direto sem registrar no `pyproject.toml`.
- ❌ Código no root do projeto em vez de `src/`.
- ❌ Pastas `models/`, `services/`, `utils/` — organize por feature/camada.
- ❌ Lock file ausente ou não commitado.
- ❌ Dependências sem range de versão (deps "soltas").
- ❌ Configuração de ferramentas em arquivos separados (`.flake8`, `mypy.ini`) quando `pyproject.toml` aceita.
- ❌ `.env` commitado.
- ❌ Versão do Python não fixada (`.python-version` ausente).
