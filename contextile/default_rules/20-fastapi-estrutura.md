# FastAPI — Estrutura e Organização

> **Aplica-se quando**: criando projeto FastAPI, organizando routers, configurando a aplicação, middlewares, ou lifecycle (startup/shutdown).

## App factory + lifespan

Use o padrão **app factory** com `lifespan` para startup/shutdown:

```python
# src/meu_app/api/app.py
from contextlib import asynccontextmanager
from fastapi import FastAPI

from meu_app.api.routers import clientes, pedidos
from meu_app.infra.db import close_db, init_db
from meu_app.api.config import Settings, get_settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    await init_db(settings.database_url)
    yield
    await close_db()

def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(
        title="Meu App",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url=None,  # uma UI basta
    )

    app.include_router(clientes.router, prefix="/v1/clientes", tags=["clientes"])
    app.include_router(pedidos.router, prefix="/v1/pedidos", tags=["pedidos"])

    return app
```

**Não** instancie `app = FastAPI()` no nível do módulo sem factory — quebra testes (não consegue passar settings diferentes) e quebra recriação de app.

`lifespan` substitui `@app.on_event("startup")` / `"shutdown"`, que estão deprecated.

## Versionamento de API

Sempre prefixe com versão (`/v1/...`). Mesmo no MVP — adicionar `/v2` depois é fácil; remover prefixo, não.

```python
app.include_router(clientes.router, prefix="/v1/clientes", tags=["clientes"])
```

## Organização de pastas

```
src/meu_app/api/
├── __init__.py
├── app.py                  # create_app + lifespan
├── config.py               # Settings (pydantic_settings)
├── deps.py                 # dependências compartilhadas (get_session, get_current_user)
├── errors.py               # exception handlers
├── middleware.py           # middlewares customizados
├── routers/
│   ├── __init__.py
│   ├── clientes.py
│   └── pedidos.py
└── schemas/                # Pydantic models (request/response)
    ├── __init__.py
    ├── cliente.py
    └── pedido.py
```

**Um arquivo por recurso** em `routers/` e `schemas/`. Quando um router passa de ~300 linhas, divida por sub-recurso.

## Anatomia de um router

```python
# src/meu_app/api/routers/clientes.py
from typing import Annotated
from fastapi import APIRouter, Depends, status

from meu_app.api.deps import SessionDep, CurrentUserDep
from meu_app.api.schemas.cliente import ClienteCreate, ClienteResponse
from meu_app.aplicacao import cliente_service

router = APIRouter()

@router.post(
    "",
    response_model=ClienteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria um novo cliente",
)
async def criar_cliente(
    payload: ClienteCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ClienteResponse:
    cliente = await cliente_service.criar(session, payload, criado_por=current_user.id)
    return ClienteResponse.model_validate(cliente, from_attributes=True)
```

Padrão de cada endpoint:

- **Prefixo do `APIRouter`** já tem o recurso — caminhos relativos (`""`, `"/{id}"`, `"/{id}/itens"`).
- **`response_model`** sempre declarado — gera OpenAPI e filtra campos.
- **`status_code`** explícito para 201/204; 200 é default e pode ficar implícito.
- **`summary`** curto e em português (vira título no Swagger).
- Handler **fino** — chama um service/use case, não tem lógica de negócio.

## App factory + middlewares

```python
def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(lifespan=lifespan, ...)

    # CORS — primeiro middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Middleware de request_id (correlação de logs)
    app.add_middleware(RequestIDMiddleware)

    # Routers
    app.include_router(...)

    # Exception handlers (ver 23-fastapi-erros.md)
    register_exception_handlers(app)

    return app
```

Ordem importa: middlewares rodam em **ordem inversa** de registro (último registrado = mais externo).

## Lifecycle — o que vai no lifespan

Use `lifespan` para recursos que precisam de **setup/teardown async**:

- Pool de conexões do banco (engine, pool HTTP).
- Conexão com Redis, RabbitMQ, Kafka.
- Cache em memória pré-carregado.
- Verificação de saúde de dependências críticas (opcional).

**Não** coloque no lifespan:

- Lógica de negócio.
- Migrations (rode separado, antes do app subir).
- Workers de background (use Celery/RQ/Arq separado, não dentro do app web).

## Health checks

Endpoint dedicado em `/health`:

```python
@router.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

Para health profundo (checa DB, cache), faça `/health/ready` separado. `/health` deve responder sempre rapidamente — orquestrador usa pra decidir matar o pod.

## Settings via dependência

```python
# api/deps.py
from functools import lru_cache
from typing import Annotated
from fastapi import Depends

from meu_app.api.config import Settings

@lru_cache
def get_settings() -> Settings:
    return Settings()

SettingsDep = Annotated[Settings, Depends(get_settings)]
```

`lru_cache` garante singleton. Em testes, sobrescreva com `app.dependency_overrides[get_settings] = lambda: Settings(...)`.

## OpenAPI

- **Tags** agrupam endpoints no Swagger (`tags=["clientes"]`).
- **Summary** curto, **description** detalhado se precisar.
- **Exemplos** em schemas: `Field(..., examples=["ana@exemplo.com"])`.
- **`response_model_exclude_unset=True`** quando faz sentido (PATCH parciais).

Para esconder OpenAPI em produção:

```python
docs_url = "/docs" if settings.environment != "prod" else None
```

## Anti-padrões

- ❌ `app = FastAPI()` no nível do módulo sem factory.
- ❌ Routes sem prefixo de versão (`/clientes` em vez de `/v1/clientes`).
- ❌ Lógica de negócio dentro do handler. Handler chama service.
- ❌ `@app.on_event("startup")` / `"shutdown"` — deprecated, use `lifespan`.
- ❌ Settings instanciado em import time fora de `lru_cache`.
- ❌ Migrations no lifespan.
- ❌ Health check que faz query pesada em DB.
- ❌ `response_model` ausente em endpoints públicos — perde validação de saída e documentação.
