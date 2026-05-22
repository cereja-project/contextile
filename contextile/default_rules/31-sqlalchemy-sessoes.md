---
apply: by model decision
instructions: Apply when configuring SQLAlchemy engine, sessionmaker, managing Session/AsyncSession lifecycle, handling transactions, or injecting session into handlers.
---

# SQLAlchemy 2.0+ — Sessões e Conexões

> **Aplica-se quando**: configurando engine, sessionmaker, gerenciando ciclo de vida de Session/AsyncSession, lidando com transações, ou injetando sessão em handlers.

## Engine — um por aplicação

`create_engine` (sync) ou `create_async_engine` (async) é **caro**. Crie **uma vez** no boot, compartilhe.

```python
# infra/db.py
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,        # detecta conexão morta antes de usar
    pool_size=10,              # conexões idle mantidas
    max_overflow=20,           # extras sob demanda
    pool_recycle=1800,         # recicla a cada 30min (evita DBs que matam conexões longas)
)

async_session = async_sessionmaker(
    engine,
    expire_on_commit=False,    # objetos continuam usáveis após commit
)
```

### `expire_on_commit=False` — quase sempre

Com `expire_on_commit=True` (default), após `commit()` todos os atributos dos objetos viram "expirados" — qualquer acesso refaz query. Com `False`, os objetos continuam usáveis.

Quase todo app web quer `False`. Excepcional manter `True` apenas em scripts longos onde stale data é problema.

### Pool sizing

Regras de bolso:

- **`pool_size`** ≈ número de workers concorrentes do app (uvicorn workers × async tasks típicas por worker).
- **`max_overflow`** ≈ 2× `pool_size` para suportar pico.
- Soma deve ser **menor que `max_connections`** do DB dividido pelo número de instâncias do app.

Monitore conexões abertas em prod — pool muito pequeno gera espera; muito grande, esgota DB.

## Sessão — uma por request/task

**Nunca compartilhe Session entre requests, threads ou tasks.** Cada operação lógica abre e fecha a sua:

```python
# api/deps.py (já mostrado em 22-fastapi-dependencias.md)
from collections.abc import AsyncIterator
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from meu_app.infra.db import async_session

async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session() as session:
        yield session

SessionDep = Annotated[AsyncSession, Depends(get_session)]
```

O `async with` garante:

- Sessão criada no início do request.
- Fechada ao final, **mesmo em caso de exceção**.
- Conexão devolvida ao pool.

## Transações — explicit > implicit

Padrão recomendado: **uma transação por request lógico**, usando `session.begin()`:

```python
async def criar_pedido(session: AsyncSession, dados: PedidoCreate) -> Pedido:
    async with session.begin():
        pedido = Pedido(...)
        session.add(pedido)
        # commit acontece ao sair do bloco sem exceção
        # rollback automático se houver exceção
    return pedido
```

Vantagens sobre `commit()` solto:

- Boundary de transação **visível** no código.
- Rollback automático em exceção.
- Compõe bem com nested transactions (savepoints) via `session.begin_nested()`.

### Padrão "transação por dependência" (alternativa)

Quando todo handler é uma transação inteira, mova o boundary pra dependência:

```python
async def get_session_tx() -> AsyncIterator[AsyncSession]:
    async with async_session() as session:
        async with session.begin():
            yield session

TxSessionDep = Annotated[AsyncSession, Depends(get_session_tx)]
```

Útil para CRUD simples. Para fluxos complexos com transações múltiplas, prefira `session.begin()` explícito.

## `session.begin_nested()` — savepoints

Para operações que precisam rollback parcial sem perder o trabalho anterior:

```python
async with session.begin():
    cliente = await criar_cliente(session, dados_cliente)

    try:
        async with session.begin_nested():
            await criar_pedido_inicial(session, cliente)
    except RegraDeNegocioViolada:
        logger.warning("pedido inicial inválido — cliente criado mesmo assim")

    # commit do begin externo persiste cliente, ignora pedido inválido
```

## Versão sync — quando aplicável

Tudo acima vale com `Session`/`sessionmaker` no lugar de `AsyncSession`/`async_sessionmaker`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionFactory = sessionmaker(engine, expire_on_commit=False)

def get_session() -> Iterator[Session]:
    with SessionFactory() as session:
        yield session
```

**Não misture sync e async no mesmo handler.** Veja `24-fastapi-sync-vs-async.md`.

## Identidade de objeto e cache de identidade

Dentro de uma mesma sessão, **o mesmo registro retorna o mesmo objeto Python**:

```python
async with async_session() as session:
    c1 = await session.get(Cliente, 1)
    c2 = await session.get(Cliente, 1)
    assert c1 is c2  # mesma instância, do cache da sessão
```

Implicações:

- Não compare objetos de **sessões diferentes** com `is`. Compare por PK ou `__eq__` customizado.
- Modificações em um objeto refletem em todas as referências dentro da sessão.
- Após `session.close()` (ou sair do `async with`), o objeto vira **detached** — acesso a atributos lazy explode.

## Detached objects — cuidado

```python
async def buscar_cliente_e_usar_fora(id: int) -> Cliente:
    async with async_session() as session:
        cliente = await session.get(Cliente, id)
    # session fechada — cliente.pedidos lança erro se for lazy
    return cliente

# uso
cliente = await buscar_cliente_e_usar_fora(1)
print(cliente.nome)         # ✅ atributo já carregado
print(cliente.pedidos)      # ❌ DetachedInstanceError se for lazy
```

Soluções:

1. **Carregue eager** o que vai usar (`selectinload(Cliente.pedidos)`).
2. **Converta para DTO/dataclass** antes de fechar a sessão.
3. **Use `session.refresh()`** ou re-merge se precisar reutilizar.

Em geral: **não deixe entidades ORM vazarem para camadas fora da sessão**. Converta para Pydantic/dataclass antes.

## `session.flush()` vs `session.commit()`

- `flush()` — emite SQL pendente, mas **não commita**. Útil quando precisa do ID gerado para usar no próprio request:
  ```python
  cliente = Cliente(...)
  session.add(cliente)
  await session.flush()
  print(cliente.id)  # já tem o ID
  ```
- `commit()` — emite SQL + commita transação. Acontece automaticamente no `async with session.begin()`.

Raramente você chama `commit()` explicitamente quando usa `begin()`.

## Rollback

`async with session.begin():` faz rollback automático em exceção. Quando não usa `begin`:

```python
try:
    session.add(obj)
    await session.commit()
except Exception:
    await session.rollback()
    raise
```

Sempre re-erga depois do rollback — engolir exceção esconde o problema.

## `pool_pre_ping=True` — sempre

Em ambientes com **proxies/firewalls** que matam conexões idle (AWS RDS, balanceadores), `pool_pre_ping=True` testa cada conexão antes de usar. Custo: ~1ms por request. Benefício: não toma `OperationalError` aleatório quando o pool tem conexão morta.

## Anti-padrões

- ❌ Engine criado dentro de função (`create_engine(...)` em cada request).
- ❌ Sessão global compartilhada entre requests/threads/tasks.
- ❌ `expire_on_commit=True` em app web (objetos viram inúteis após commit).
- ❌ `commit()` espalhado pelo código sem `begin()` claro.
- ❌ Sem `pool_pre_ping=True` em ambientes com conexões mortas frequentes.
- ❌ Esquecer `rollback()` em código que faz `commit()` manual.
- ❌ Acessar atributo lazy de objeto detached (sessão fechada).
- ❌ Entidade ORM vazando para resposta HTTP sem converter para schema.
- ❌ Misturar `Session` (sync) e `AsyncSession` (async) no mesmo handler.
- ❌ Pool gigante (`pool_size=100`) "por segurança" — esgota DB.
