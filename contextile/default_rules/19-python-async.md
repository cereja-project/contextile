---
apply: by model decision
instructions: Apply when writing async def code, using asyncio, handling I/O concurrency, or deciding between sync and async.
---

# Python — Async (asyncio 3.12+)

> **Aplica-se quando**: escrevendo código `async def`, usando `asyncio`, lidando com concorrência I/O, ou decidindo entre sync e async.
>
> **Complementa**: `1B-python-concorrencia.md` (escolha entre asyncio, threading, multiprocessing — para CPU bound ou libs sync, ver aquele arquivo).

## Quando usar async

Async é útil para **I/O concorrente**:

- ✅ Múltiplas chamadas HTTP em paralelo.
- ✅ Servidor web com muitas conexões simultâneas (FastAPI, aiohttp).
- ✅ Consumo de filas, websockets, streaming.
- ✅ Acesso a banco de dados com muitas queries pequenas concorrentes.

Async **não ajuda** para:

- ❌ Trabalho CPU-bound (parsing pesado, criptografia, ML). Use `ProcessPoolExecutor` ou serviço separado.
- ❌ Operações sequenciais sem espera por I/O.
- ❌ Scripts simples de uma chamada por vez — adiciona complexidade sem ganho.

## Regra de ouro: sem misturar

Uma vez em código `async`, **todo I/O é async**. Misturar uma chamada `requests.get()` no meio de uma função `async` bloqueia o event loop inteiro — todas as outras tarefas pausam.

```python
# ❌ requests bloqueia o loop
async def buscar(url: str) -> dict:
    resp = requests.get(url)  # blocking!
    return resp.json()

# ✅ httpx async
async def buscar(url: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        return resp.json()
```

Equivalências comuns:

| Sync (bloqueia)   | Async (não bloqueia)             |
| ----------------- | -------------------------------- |
| `requests`        | `httpx.AsyncClient` ou `aiohttp` |
| `time.sleep(s)`   | `await asyncio.sleep(s)`         |
| `open().read()`   | `aiofiles.open()` ou `to_thread` |
| `psycopg`         | `psycopg` async ou `asyncpg`     |
| `redis-py` (sync) | `redis-py` async                 |

## Bloqueante inevitável: `asyncio.to_thread`

Quando você **precisa** chamar código bloqueante (lib sem versão async), isole em thread:

```python
import asyncio

async def processar(payload: bytes) -> dict:
    # decode_pesado é função síncrona pesada
    resultado = await asyncio.to_thread(decode_pesado, payload)
    return resultado
```

`to_thread` libera o loop enquanto a thread roda. Use com moderação — abusar mata a vantagem do async.

## Estruturação de concorrência

### `asyncio.TaskGroup` (3.11+) — preferido

```python
async def buscar_dashboard(user_id: int) -> Dashboard:
    async with asyncio.TaskGroup() as tg:
        perfil = tg.create_task(buscar_perfil(user_id))
        pedidos = tg.create_task(listar_pedidos(user_id))
        notif = tg.create_task(buscar_notificacoes(user_id))

    return Dashboard(perfil=perfil.result(), pedidos=pedidos.result(), notif=notif.result())
```

Vantagens sobre `gather`:

- **Concorrência estruturada**: se uma tarefa falhar, as outras são canceladas automaticamente.
- Exceções viram **`ExceptionGroup`** — capture com `except*`.
- Escopo claro (`async with`) — não vaza tasks.

### `asyncio.gather` — quando precisa de `return_exceptions=True`

Use só quando você **quer** continuar mesmo com falhas parciais:

```python
resultados = await asyncio.gather(
    buscar_perfil(user_id),
    listar_pedidos(user_id),
    buscar_notificacoes(user_id),
    return_exceptions=True,
)
# resultados pode conter exceções; inspecione antes de usar
```

Em código novo, **prefira `TaskGroup`**. `gather` fica para casos legítimos de "tolerância parcial".

## Timeout

Use `asyncio.timeout()` (3.11+):

```python
async def buscar_com_timeout() -> dict:
    async with asyncio.timeout(5.0):
        return await chamada_lenta()
```

Não use `asyncio.wait_for(...)` em código novo — `timeout` é mais limpo e compõe melhor com `TaskGroup`.

## Limitar concorrência: Semaphore

Para evitar saturar APIs externas ou recursos:

```python
async def baixar_todos(urls: list[str]) -> list[bytes]:
    sem = asyncio.Semaphore(10)  # máximo 10 simultâneas

    async def baixar_um(url: str) -> bytes:
        async with sem:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url)
                return resp.content

    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(baixar_um(u)) for u in urls]

    return [t.result() for t in tasks]
```

## Tratamento de exceções com `ExceptionGroup`

`TaskGroup` agrega exceções. Use `except*`:

```python
try:
    async with asyncio.TaskGroup() as tg:
        tg.create_task(chamada_a())
        tg.create_task(chamada_b())
except* ValueError as eg:
    for e in eg.exceptions:
        logger.warning("validação: %s", e)
except* httpx.HTTPError as eg:
    logger.exception("falha de rede")
    raise
```

`except*` filtra dentro do grupo; outras exceções continuam propagando.

## Cancelamento

`asyncio.CancelledError` **deve ser reerguida**:

```python
async def operacao() -> None:
    try:
        await trabalho_demorado()
    except asyncio.CancelledError:
        logger.info("operação cancelada, limpando")
        await limpar()
        raise  # ✅ sempre reergua
    except Exception:
        logger.exception("erro inesperado")
        raise
```

Engolir `CancelledError` quebra a propagação de cancelamento — `TaskGroup` e timeouts param de funcionar.

## Context managers async

Recursos com setup/teardown async usam `async with`:

```python
async with httpx.AsyncClient(timeout=10) as client:
    resp = await client.get(url)

async with aiofiles.open(path, "rb") as f:
    dados = await f.read()
```

Para criar context manager async customizado, `@asynccontextmanager`:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def transacao(session: AsyncSession):
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
```

## Fire-and-forget: cuidado

`asyncio.create_task(...)` **sem guardar a referência** pode ser garbage-collected antes de completar:

```python
# ❌ task pode ser coletada
asyncio.create_task(enviar_metrica(evento))

# ✅ guarde a referência
_background_tasks: set[asyncio.Task] = set()

def disparar(coro):
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
```

Em FastAPI, prefira `BackgroundTasks` (documentado em regra de FastAPI).

## Async em testes

Use `pytest-asyncio` com `mode = "auto"` em `pyproject.toml`. Não cubro detalhes aqui — veja `02-pytest-fixtures.md` para fixtures e `04-pytest-mocks.md` para mocks async.

## Anti-padrões

- ❌ Chamar função sync bloqueante dentro de `async def` sem `to_thread`.
- ❌ `time.sleep(s)` em código async. Use `await asyncio.sleep(s)`.
- ❌ Esquecer `await` (`await` em coroutines, nunca em valores comuns).
- ❌ `asyncio.gather` quando `TaskGroup` resolve melhor.
- ❌ `asyncio.wait_for` em código novo (use `asyncio.timeout`).
- ❌ Engolir `CancelledError` sem reerguer.
- ❌ `create_task` sem manter referência.
- ❌ Misturar `threading` com `asyncio` sem `to_thread` ou `loop.run_in_executor`.
- ❌ Usar `async` "para o caso de precisar" — adiciona complexidade. Comece sync; migre para async quando houver ganho claro.