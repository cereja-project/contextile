---
apply: by model decision
instructions: Apply when configuring pytest markers, adjusting test discovery, defining execution options, or integrating pytest-asyncio/pytest-cov.
---

# Pytest — Organização e Configuração

> **Aplica-se quando**: configurando markers, ajustando descoberta de testes, definindo opções de execução, ou integrando pytest-asyncio/pytest-cov.
>
> **Complementa**: `04-test-organizacao.md` (princípios gerais de organização).

## Configuração centralizada em `pyproject.toml`

Todos os ajustes do pytest ficam em `[tool.pytest.ini_options]`. **Não** use `pytest.ini` separado em projeto novo.

```toml
[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "-ra --strict-markers --strict-config"
filterwarnings = [
    "error",                                  # warning vira erro por padrão
    "ignore::DeprecationWarning:lib_legada",  # exceções pontuais
]
markers = [
    "slow: testes lentos (>1s)",
    "integration: requer banco/serviços externos",
    "e2e: ponta a ponta",
]
```

Pontos importantes:

- **`pythonpath = ["src"]`** — necessário para projetos com layout `src/`.
- **`--strict-markers`** — marcador não registrado vira erro (não warning silencioso).
- **`--strict-config`** — opção desconhecida em `pyproject.toml` quebra.
- **`-ra`** — resumo de **todas** as outras saídas no fim (skip, xfail, errors). `-r` sem `a` mostra menos.
- **`filterwarnings = ["error"]`** — força você a tratar warnings (ou silenciar explicitamente).

## Descoberta de testes

Convenções obedecidas por padrão (não precisa configurar):

- **Pastas/arquivos**: `test_*.py` ou `*_test.py`.
- **Classes**: `Test*` (sem `__init__`).
- **Funções/métodos**: `test_*`.

**Não** mude essas convenções via `python_files`, `python_classes`, `python_functions` exceto em projeto legado. Manter o padrão facilita onboarding e integração com ferramentas.

## Markers

### Registro obrigatório

Com `--strict-markers`, todo marker deve estar declarado em `pyproject.toml`:

```toml
markers = [
    "slow: testes lentos (>1s)",
    "integration: requer banco/serviços externos",
    "e2e: ponta a ponta",
    "skip_ci: pular em CI",
]
```

Sem registro, `@pytest.mark.foo` quebra a execução — pega typos.

### Aplicação

```python
@pytest.mark.slow
@pytest.mark.integration
def test_importacao_de_planilha_grande(): ...
```

Markers em **classe** valem para todos os métodos:

```python
@pytest.mark.integration
class TestPedidoRepository: ...
```

Markers em **módulo inteiro** (no topo do arquivo):

```python
import pytest

pytestmark = pytest.mark.integration

# todos os testes deste arquivo herdam o marker
```

## Execução seletiva

Combinando markers e expressões:

```bash
pytest -m "unit"                  # só unit
pytest -m "not slow"              # pula lentos
pytest -m "integration and not slow"  # integração rápida
pytest -k "vip"                   # nome contém "vip"
pytest -k "test_cliente and not test_cliente_legacy"
pytest tests/unit                 # só pasta unit
pytest --lf                       # last failed
pytest --ff                       # failed first, depois resto
```

CI pipelines padrão:

```bash
# pipeline rápido (PR)
pytest -m "not slow and not e2e"

# pipeline completo (merge to main)
pytest

# pipeline de integração (separado)
pytest -m "integration"
```

## pytest-asyncio

Para projetos async, configure modo automático em `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

Com `auto`, todas as funções `async def test_*` e fixtures `async def` são tratadas automaticamente — sem precisar de `@pytest.mark.asyncio` em cada teste.

Sem `auto` (modo `strict`), cada teste async precisa do decorador:

```python
@pytest.mark.asyncio
async def test_busca(): ...
```

**Recomendado**: `auto`. Menos boilerplate, menos chance de esquecer.

## pytest-cov — cobertura

Não instale `coverage` separado — use `pytest-cov`:

```bash
pytest --cov=src --cov-report=term-missing --cov-report=html
```

Configuração em `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["src"]
branch = true
omit = [
    "*/migrations/*",
    "*/__main__.py",
]

[tool.coverage.report]
show_missing = true
skip_covered = false
exclude_lines = [
    "pragma: no cover",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.:",
]
```

`branch = true` mede cobertura de ramificações (não só linhas). Mais rigoroso.

Para falhar build abaixo de threshold:

```toml
[tool.coverage.report]
fail_under = 80
```

Veja `04-test-organizacao.md` para a filosofia de cobertura.

## Plugins úteis

Adicione ao grupo de teste em `pyproject.toml`:

```toml
[dependency-groups]
test = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-mock>=3.14",
    "pytest-cov>=5.0",
    "freezegun>=1.5",
    "factory-boy>=3.3",
    "httpx>=0.27",          # cliente HTTP para testes de FastAPI
    "pytest-randomly>=3.15", # randomiza ordem dos testes (pega dependências de ordem)
]
```

`pytest-randomly` é especialmente útil: roda testes em ordem aleatória a cada execução. Testes com dependência implícita de ordem **quebram rapidamente** — pega o bug cedo.

## Conftest no nível certo

Lembrando da regra de `06-pytest-fixtures.md`:

- `tests/conftest.py` — fixtures globais (app, settings).
- `tests/unit/conftest.py` — fixtures de unitários.
- `tests/integration/conftest.py` — fixtures de integração (DB, container).
- `tests/e2e/conftest.py` — fixtures e2e (cliente HTTP, fluxo completo).

Conftest mais próximo do teste sobrescreve ancestrais.

## Output e debug

```bash
pytest -v                  # verbose: mostra cada teste
pytest -s                  # não captura stdout — print() aparece
pytest --tb=short          # tracebacks curtos
pytest --tb=long           # tracebacks completos (default)
pytest -x                  # stop on first failure
pytest --maxfail=3         # stop após 3 falhas
pytest -lf                 # last failed
pytest --pdb               # entra no pdb na primeira falha
```

`-s` desabilita captura — útil em debug local, **nunca** em CI (output pode conter dados sensíveis).

## Anti-padrões pytest-organização-específicos

- ❌ Markers não registrados em `pyproject.toml` — quebram em `--strict-markers`.
- ❌ `pytest.ini` em projeto novo. Use `pyproject.toml`.
- ❌ Mudar `python_files`/`python_functions` por preferência pessoal — quebra ferramentas.
- ❌ Sem `--strict-markers` e `--strict-config` em `addopts` — typos passam.
- ❌ Cobertura de 100% como meta — gera testes vazios. Veja `04-test-organizacao.md`.
- ❌ `asyncio_mode = "strict"` em projeto async novo — adiciona boilerplate sem benefício.
- ❌ `pytest -s` em CI — vaza dados sensíveis nos logs.
