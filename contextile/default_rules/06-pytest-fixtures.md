---
apply: by model decision
instructions: Apply when creating or modifying pytest fixtures, conftest.py files, factories (factory_boy or manual builders), or test helper functions.
---

# Pytest — Fixtures e Conftest

> **Aplica-se quando**: criando ou modificando fixtures pytest, arquivos `conftest.py`, factories (factory_boy ou builders manuais) ou helpers de teste em projetos que usam pytest.
>
> **Complementa**: `00-test-principios.md` (onde DRY se aplica) e `02-test-isolamento.md` (conceito de isolamento).

## Regras de fixtures

1. **Prefira fixtures a `setUp`/`tearDown` xUnit.** Não herde de `unittest.TestCase` exceto em código legado.
2. Use o **escopo mais restrito possível**: `function` (padrão) > `class` > `module` > `session`. Só amplie quando o custo de setup justificar.
3. Use `yield` para teardown:
   ```python
   @pytest.fixture
   def db_session():
       session = create_session()
       yield session
       session.rollback()
       session.close()
   ```
4. **Nomes descritivos**: `usuario_admin_logado`, não `user1`.
5. Para variações da mesma fixture, use `params=[...]`:
   ```python
   @pytest.fixture(params=["sqlite", "postgres"], ids=["sqlite", "postgres"])
   def db(request):
       ...
   ```

## Escopos — quando usar cada

- **`function`** (default) — recriada a cada teste. Use sempre que dá. Garante isolamento.
- **`class`** — compartilhada entre métodos da mesma classe `TestX`. Raramente útil sem `unittest.TestCase`.
- **`module`** — uma por arquivo de teste. Útil para setup caro **e** imutável dentro do módulo (ex: cliente HTTP de leitura).
- **`session`** — uma por execução de `pytest`. Use só para recursos verdadeiramente compartilháveis (engine de DB read-only, container Docker iniciado uma vez).

Quanto maior o escopo, maior o risco de **vazamento de estado** entre testes. Justifique cada ampliação.

## `conftest.py` — hierarquia e regras

- `conftest.py` vive no **nível mais próximo** dos testes que usam suas fixtures.
- A hierarquia segue a estrutura de pastas: fixtures em `tests/unit/conftest.py` só valem dentro de `tests/unit/`.
- **Não duplique** fixtures entre `conftest.py` — mova para o ancestral comum.
- `conftest.py` na raiz `tests/` para fixtures globais; em subpastas, para fixtures específicas daquele escopo.

```
tests/
├── conftest.py            # fixtures usadas em todos os testes (app, settings de teste)
├── unit/
│   └── conftest.py        # fixtures só de unitários
├── integration/
│   └── conftest.py        # fixtures de integração (DB real, container)
└── e2e/
    └── conftest.py        # fixtures e2e (cliente HTTP, fluxo completo)
```

## `request` para introspecção

A fixture especial `request` dá acesso ao contexto do teste:

```python
@pytest.fixture
def temp_file(request, tmp_path):
    file = tmp_path / f"{request.node.name}.txt"
    file.write_text("data")
    return file
```

Útil para fixtures que precisam saber qual teste está rodando (nomes únicos, paths por teste).

## Factories

Para criar entidades de domínio com defaults sensatos:

### `factory_boy` (recomendado)

```python
import factory
from meu_app.dominio.cliente import Cliente, TipoCliente

class ClienteFactory(factory.Factory):
    class Meta:
        model = Cliente

    id = factory.Sequence(lambda n: n + 1)
    nome = factory.Faker("name", locale="pt_BR")
    email = factory.LazyAttribute(lambda o: f"{o.nome.lower().replace(' ', '.')}@x.com")
    tipo = TipoCliente.COMUM
```

Uso:

```python
def test_cliente_vip_tem_desconto():
    cliente = ClienteFactory(tipo=TipoCliente.VIP)
    assert cliente.tem_desconto() is True
```

O override (`tipo=TipoCliente.VIP`) destaca o que importa no teste — DAMP. O resto vem dos defaults — DRY.

### Builder manual (alternativa simples)

```python
def cliente_factory(
    *,
    nome: str = "Cliente Teste",
    email: str = "teste@x.com",
    tipo: TipoCliente = TipoCliente.COMUM,
    **kwargs,
) -> Cliente:
    return Cliente(nome=nome, email=email, tipo=tipo, **kwargs)
```

Use builder manual quando o projeto é pequeno ou a entidade tem poucos campos. `factory_boy` ganha quando há muitas entidades relacionadas (`SubFactory`, `RelatedFactory`).

## Helpers utilitários

Para ações que **não são o foco do teste** (login, popular DB, etc.):

```python
# tests/fixtures/auth.py
async def realizar_login(client: AsyncClient, email: str = "admin@x.com") -> str:
    resp = await client.post("/v1/auth/login", json={"email": email, "senha": "..."})
    return resp.json()["access_token"]
```

Helpers fazem **uma coisa só**, com nome no imperativo. Não passem por flags (`helper(login=True, criar_pedido=True)`).

## Fixtures async (pytest-asyncio)

Use `@pytest_asyncio.fixture` ou (com `asyncio_mode = "auto"`) apenas `@pytest.fixture`:

```python
@pytest_asyncio.fixture
async def async_session() -> AsyncIterator[AsyncSession]:
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()
```

Configuração em `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

Com `asyncio_mode = "auto"`, todas as funções `async def` (testes e fixtures) são tratadas automaticamente.

## Sobrescrita em testes

Para substituir uma fixture específica em um arquivo/diretório, basta declarar com o mesmo nome em `conftest.py` mais próximo:

```python
# tests/integration/conftest.py
@pytest.fixture
def db_session():
    # versão para integração — usa DB real
    ...
```

A fixture mais próxima do teste **sobrescreve** as ancestrais.

## Anti-padrões pytest-específicos

- ❌ `@pytest.fixture(scope="session")` para fixtures mutáveis — vaza estado entre testes.
- ❌ Fixture chamando `mocker.patch` direto (mistura escopo) — prefira retornar o mock e injetar.
- ❌ Esquecer `pytest_asyncio.fixture` em fixtures async sem `asyncio_mode = "auto"`.
- ❌ Cadeia de fixtures com 5+ dependências para um teste simples — refatore.
- ❌ Lógica de teste (asserções, Act) dentro de fixture.
- ❌ Fixtures que retornam estados diferentes via `request.param` sem `ids=` — falhas ilegíveis no relatório.
