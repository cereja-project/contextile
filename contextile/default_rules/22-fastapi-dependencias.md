# FastAPI — Dependências (`Depends`)

> **Aplica-se quando**: declarando dependências em handlers, criando dependências reutilizáveis (DB session, autenticação, paginação), ou configurando overrides para testes.

## Sintaxe moderna: `Annotated`

Use `Annotated[Tipo, Depends(...)]` em vez de default `= Depends(...)`. É o estilo recomendado pela documentação atual e funciona melhor com type checkers e refatoração:

```python
from typing import Annotated
from fastapi import Depends

# ✅ moderno
async def handler(session: Annotated[AsyncSession, Depends(get_session)]) -> ...:
    ...

# ❌ estilo antigo
async def handler(session: AsyncSession = Depends(get_session)) -> ...:
    ...
```

Vantagens:

- Sobrevive a refatorações sem precisar reordenar argumentos.
- Permite empilhar metadados (`Annotated[X, Depends(...), Path(...)]`).
- Funciona melhor com `dependency_overrides` em testes.

## Aliases de tipo para reuso

Crie aliases nomeados para dependências usadas em todo lugar:

```python
# api/deps.py
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from meu_app.infra.db import get_session
from meu_app.dominio.usuario import Usuario

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Usuario:
    ...

SessionDep = Annotated[AsyncSession, Depends(get_session)]
CurrentUserDep = Annotated[Usuario, Depends(get_current_user)]
```

Uso nos handlers:

```python
@router.get("/me")
async def me(usuario: CurrentUserDep) -> UsuarioResponse: ...

@router.post("/pedidos")
async def criar(payload: PedidoCreate, session: SessionDep, usuario: CurrentUserDep) -> ...: ...
```

Menos boilerplate, mais legível, e mudar a implementação só toca `deps.py`.

## Sessão de banco como dependência

Padrão **uma sessão por request**, fechada ao final:

```python
# infra/db.py
from collections.abc import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session() as session:
        yield session
```

Detalhes em `31-sqlalchemy-sessoes.md`. Aqui o ponto é o **padrão `yield`** — recurso aberto antes do handler, fechado depois (mesmo em caso de erro).

## Autenticação como dependência

```python
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/token")

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: SessionDep,
) -> Usuario:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail="token inválido") from e

    usuario = await usuario_repo.buscar(session, payload["sub"])
    if usuario is None or not usuario.ativo:
        raise HTTPException(status_code=401, detail="usuário inválido")

    return usuario

CurrentUserDep = Annotated[Usuario, Depends(get_current_user)]
```

Para checar **permissões**, componha:

```python
def requer_papel(papel: str):
    async def _checar(usuario: CurrentUserDep) -> Usuario:
        if papel not in usuario.papeis:
            raise HTTPException(status_code=403, detail="acesso negado")
        return usuario
    return _checar

AdminDep = Annotated[Usuario, Depends(requer_papel("admin"))]
```

Uso:

```python
@router.delete("/{id}")
async def remover(id: int, _: AdminDep, session: SessionDep) -> None: ...
```

`_` no parâmetro indica "presença obrigatória, valor não usado".

## Paginação como dependência

```python
from fastapi import Query

class PaginaParams(BaseModel):
    cursor: str | None = None
    limite: int = Field(default=20, ge=1, le=100)

async def pagina_params(
    cursor: Annotated[str | None, Query()] = None,
    limite: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginaParams:
    return PaginaParams(cursor=cursor, limite=limite)

PaginaDep = Annotated[PaginaParams, Depends(pagina_params)]
```

Uso:

```python
@router.get("", response_model=Pagina[ClienteResponse])
async def listar(pag: PaginaDep, session: SessionDep) -> Pagina[ClienteResponse]: ...
```

## Sub-dependências

Dependências podem depender de outras. FastAPI resolve a árvore:

```python
async def get_repo(session: SessionDep) -> ClienteRepository:
    return ClienteRepository(session)

RepoDep = Annotated[ClienteRepository, Depends(get_repo)]

@router.get("")
async def listar(repo: RepoDep) -> list[ClienteResponse]: ...
```

Cada dependência é resolvida **uma vez por request** (cache automático), então o `session` é compartilhado entre todas as deps do mesmo request.

Para forçar nova instância por uso, `Depends(get_session, use_cache=False)`.

## Dependências com setup/teardown

`yield` permite setup antes e teardown depois (mesmo em caso de exceção):

```python
async def with_transaction(session: SessionDep) -> AsyncIterator[AsyncSession]:
    async with session.begin():
        yield session
        # commit acontece automaticamente ao sair do with se não houve exceção

TxDep = Annotated[AsyncSession, Depends(with_transaction)]
```

## Override em testes

```python
# tests/conftest.py
import pytest
from httpx import AsyncClient, ASGITransport

from meu_app.api.app import create_app
from meu_app.api.deps import get_session, get_current_user

@pytest.fixture
async def app():
    app = create_app(test_settings)

    app.dependency_overrides[get_session] = lambda: session_de_teste
    app.dependency_overrides[get_current_user] = lambda: usuario_de_teste

    yield app
    app.dependency_overrides.clear()

@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
```

**Sempre** limpe `dependency_overrides` no teardown da fixture — vazamento entre testes vira flakiness.

## Escopo das dependências

FastAPI **não tem** escopos hierárquicos (request-scoped, app-scoped) como Spring/Django. Toda dep é **request-scoped por padrão**.

Para **app-scoped** (singleton), use `lru_cache`:

```python
@lru_cache
def get_settings() -> Settings:
    return Settings()
```

Para recursos com lifecycle longo (engine, cliente HTTP), inicialize no `lifespan` e injete via dependência que retorna do `app.state`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient()
    yield
    await app.state.http_client.aclose()

def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client

HttpClientDep = Annotated[httpx.AsyncClient, Depends(get_http_client)]
```

## Anti-padrões

- ❌ `= Depends(...)` em vez de `Annotated[X, Depends(...)]`.
- ❌ Sessão de DB criada dentro do handler em vez de injetada.
- ❌ Dependência sem `yield` quando precisa de cleanup (vaza recurso).
- ❌ `dependency_overrides` sem `clear()` no teardown.
- ❌ Lógica de autenticação inline no handler em vez de dependência.
- ❌ Settings recriado a cada request (sem `lru_cache`).
- ❌ Compartilhar a mesma `session` entre múltiplos requests (acoplamento concorrente).
- ❌ `HTTPException` levantada dentro do service de domínio. Service levanta exceção de domínio; handler/dep converte para HTTP.
