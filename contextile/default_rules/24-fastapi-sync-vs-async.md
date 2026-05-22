# FastAPI — Sync vs Async

> **Aplica-se quando**: decidindo entre `def` e `async def` em handlers/dependências, lidando com chamadas bloqueantes, ou configurando background tasks.

> Complementa: `19-python-async.md` (regras gerais de asyncio).

## Como o FastAPI executa cada estilo

- **`async def`** roda no event loop principal. Tudo o que faz `I/O` precisa ser `await` em libs async.
- **`def`** roda em um **threadpool externo** automaticamente. Pode usar libs sync sem bloquear o loop — mas cada request consome uma thread.

## Quando usar `async def`

Use `async def` quando o handler/dep **realmente faz I/O async**:

```python
@router.get("/{id}")
async def buscar(id: int, session: SessionDep) -> ClienteResponse:
    cliente = await session.get(Cliente, id)        # SQLAlchemy async
    notas = await client.get(f"/notas/{id}")         # httpx async
    return ClienteResponse.model_validate(cliente, from_attributes=True)
```

Critério: se a função tem **pelo menos um `await` que faz I/O** (DB, HTTP, fila, cache), seja `async def`.

## Quando usar `def`

Use `def` quando o handler **só usa libs sync** ou faz trabalho CPU-bound leve:

```python
@router.post("/calcular")
def calcular_imposto(payload: ImpostoRequest) -> ImpostoResponse:
    resultado = calcular(payload.valor, payload.aliquota)  # cálculo puro
    return ImpostoResponse(valor=resultado)
```

Não force `async def` se não há `await` real. Adicionar `async` "por consistência" engana o leitor — sugere I/O onde não há.

## Regra de ouro: nunca misture sync bloqueante em `async def`

O pior cenário é `async def` chamando `requests.get()`, `time.sleep()`, ou SQLAlchemy sync. **Bloqueia o loop inteiro** — todas as outras requests do worker param.

```python
# ❌ catástrofe
@router.get("/dashboard")
async def dashboard() -> Dashboard:
    response = requests.get(url)             # sync — bloqueia o loop
    rows = sync_session.execute(...).all()   # sync — bloqueia o loop
    ...

# ✅ tudo async
@router.get("/dashboard")
async def dashboard(session: AsyncSessionDep) -> Dashboard:
    response = await httpx_client.get(url)
    rows = (await session.execute(select(...))).scalars().all()
    ...

# ✅ ou tudo sync (handler def, lib sync)
@router.get("/dashboard")
def dashboard(session: SyncSessionDep) -> Dashboard:
    response = requests.get(url)
    rows = session.execute(select(...)).scalars().all()
    ...
```

Se o handler é `async def`, **toda dependência também deve ser async**, e toda chamada bloqueante isolada em `asyncio.to_thread(...)`.

## Bloqueante inevitável: `asyncio.to_thread`

Para libs que não têm versão async (PDF, OCR, parsing pesado):

```python
import asyncio
from reportlab.pdfgen import canvas

@router.post("/relatorio")
async def gerar(payload: RelatorioRequest) -> Response:
    pdf_bytes = await asyncio.to_thread(gerar_pdf_sync, payload)
    return Response(content=pdf_bytes, media_type="application/pdf")

def gerar_pdf_sync(payload: RelatorioRequest) -> bytes:
    # lib sync, pode ser pesada
    ...
```

`to_thread` libera o loop enquanto a thread roda. Use com **moderação** — abusar mata a vantagem do async.

## Escolha por feature, não por projeto

O FastAPI suporta os dois estilos no **mesmo app**. Cada endpoint escolhe o seu:

```python
@router.get("/clientes/{id}")
async def buscar(...) -> ClienteResponse: ...   # async (DB async)

@router.post("/relatorio/csv")
def gerar_csv(...) -> Response: ...              # sync (CSV grande, lib sync, threadpool)
```

Critério prático:

- Endpoints com **DB e HTTP externo** → `async def` + libs async.
- Endpoints com **trabalho CPU-bound moderado** ou **libs sync sem alternativa** → `def`.
- Trabalho **CPU-bound pesado** (segundos) → não rode no FastAPI. Use worker (Celery, RQ, Arq).

## `BackgroundTasks` — quando usar

`BackgroundTasks` roda **depois da resposta** ser enviada, no mesmo processo. Útil para "fire-and-forget" leve:

```python
from fastapi import BackgroundTasks

@router.post("/clientes")
async def criar(
    payload: ClienteCreate,
    session: SessionDep,
    background: BackgroundTasks,
) -> ClienteResponse:
    cliente = await cliente_service.criar(session, payload)
    background.add_task(enviar_boas_vindas, cliente.email)
    return ClienteResponse.model_validate(cliente, from_attributes=True)
```

Apropriado para:

- Envio de e-mail/SMS pós-cadastro.
- Log/auditoria que pode atrasar.
- Invalidação de cache.

**Não** use para:

- Trabalho pesado (segundos+) — bloqueia recursos do worker.
- Operação que **precisa** completar (sem garantia de execução se o processo cair).
- Retry, agendamento, fanout — use fila externa (RabbitMQ, SQS, Redis Streams) + worker dedicado.

## Lifespan: async by default

`lifespan` é sempre `async def` — mesmo se o conteúdo é sync. Use `to_thread` quando precisar:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db_async()
    # se algum setup é sync pesado:
    await asyncio.to_thread(carregar_modelos_ml)
    yield
    await close_db_async()
```

## Streaming responses

Para grandes volumes, retorne `StreamingResponse` com generator async:

```python
from fastapi.responses import StreamingResponse

@router.get("/export.csv")
async def exportar(session: SessionDep) -> StreamingResponse:
    async def gerar() -> AsyncIterator[bytes]:
        yield b"id,nome,email\n"
        async for cliente in cliente_service.iter_todos(session):
            yield f"{cliente.id},{cliente.nome},{cliente.email}\n".encode()

    return StreamingResponse(gerar(), media_type="text/csv")
```

Evita carregar tudo em memória; cliente recebe os dados conforme são produzidos.

## WebSockets

Sempre `async def` — não há versão sync de WebSocket no FastAPI:

```python
@router.websocket("/ws/{cliente_id}")
async def ws(websocket: WebSocket, cliente_id: int) -> None:
    await websocket.accept()
    try:
        async for mensagem in websocket.iter_text():
            ...
    except WebSocketDisconnect:
        ...
```

## Como decidir, rapidamente

Pergunta única: **a função faz `await` em I/O?**

- Sim → `async def` + tudo async ou `to_thread` para bloqueante isolado.
- Não → `def` (FastAPI cuida da threadpool).
- Trabalho pesado (segundos+) → fora do FastAPI (worker).

## Anti-padrões

- ❌ `async def` chamando `requests.get`, `time.sleep`, ou SQLAlchemy sync.
- ❌ `async def` sem nenhum `await` — está mentindo sobre o que faz.
- ❌ Sessão sync injetada em handler `async def` ou vice-versa.
- ❌ `BackgroundTasks` para trabalho que precisa garantia de execução.
- ❌ Trabalho CPU-bound pesado em handler — saturar workers afeta latência geral.
- ❌ Misturar libs HTTP sync (`requests`) e async (`httpx.AsyncClient`) no mesmo handler async.
- ❌ Loop manual sobre threadpool em vez de `to_thread`/`run_in_executor`.
