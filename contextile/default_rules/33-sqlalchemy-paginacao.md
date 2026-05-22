---
apply: by model decision
instructions: Apply when paginating result sets — especially in large tables —, deciding between offset/limit and keyset (cursor) pagination, or dealing with total count of results.
---

# SQLAlchemy 2.0+ — Paginação para Grandes Volumes

> **Aplica-se quando**: paginando listagens, especialmente em tabelas grandes; decidindo entre offset/limit e keyset (cursor); ou lidando com contagem total de resultados.

## Por que offset/limit não escala

A paginação tradicional usa `OFFSET N LIMIT K`:

```sql
SELECT * FROM pedidos ORDER BY criado_em DESC OFFSET 10000 LIMIT 20;
```

Problema: o banco precisa **escanear e descartar** 10.000 linhas antes de retornar 20. Custo cresce linearmente com a profundidade da página.

Em listagens curtas (< ~1.000 registros), offset é aceitável. Em listagens grandes, **vira gargalo silencioso**.

### Quando offset/limit está OK

- Datasets pequenos (< 1.000 registros totais).
- UIs administrativas pouco acessadas.
- Quando você precisa de "ir para página N" arbitrária.

### Quando trocar para keyset

- Tabelas com > 10.000 registros.
- Endpoints de alta frequência (feeds, listagens públicas).
- Quando latência de páginas profundas começa a ser visível.

## Keyset pagination (cursor)

A ideia: em vez de "pular N linhas", filtre **`WHERE coluna_ordenada > último_valor_visto`**.

```sql
-- Em vez de OFFSET 10000:
SELECT * FROM pedidos
WHERE (criado_em, id) < ('2026-05-01 10:00:00', 12345)
ORDER BY criado_em DESC, id DESC
LIMIT 20;
```

Custo **constante** independente de quão profundo o cliente vai — usa índice direto.

### Implementação em SQLAlchemy

```python
from base64 import urlsafe_b64encode, urlsafe_b64decode
from datetime import datetime
import json

from sqlalchemy import select, tuple_, and_

from meu_app.api.schemas.pagina import Pagina

LIMITE_PADRAO = 20
LIMITE_MAXIMO = 100

async def listar_pedidos(
    session: AsyncSession,
    cursor: str | None = None,
    limite: int = LIMITE_PADRAO,
) -> Pagina[Pedido]:
    limite = min(limite, LIMITE_MAXIMO)

    stmt = (
        select(Pedido)
        .order_by(Pedido.criado_em.desc(), Pedido.id.desc())
        .limit(limite + 1)  # busca 1 extra pra saber se há próxima página
    )

    if cursor:
        criado_em, id_ = _decodificar_cursor(cursor)
        stmt = stmt.where(
            tuple_(Pedido.criado_em, Pedido.id) < (criado_em, id_)
        )

    resultados = (await session.scalars(stmt)).all()

    tem_proxima = len(resultados) > limite
    itens = resultados[:limite]

    proximo_cursor: str | None = None
    if tem_proxima and itens:
        ultimo = itens[-1]
        proximo_cursor = _codificar_cursor(ultimo.criado_em, ultimo.id)

    return Pagina(itens=itens, proximo_cursor=proximo_cursor)

def _codificar_cursor(criado_em: datetime, id_: int) -> str:
    payload = json.dumps({"c": criado_em.isoformat(), "id": id_})
    return urlsafe_b64encode(payload.encode()).decode()

def _decodificar_cursor(cursor: str) -> tuple[datetime, int]:
    payload = json.loads(urlsafe_b64decode(cursor.encode()))
    return datetime.fromisoformat(payload["c"]), payload["id"]
```

Pontos críticos:

- **Ordenação composta** (`criado_em, id`) — `criado_em` sozinho não desempata; sem desempate o cursor pula registros com mesmo timestamp.
- **Coluna(s) do cursor devem ter índice** — sem isso, perde toda a vantagem.
- **`tuple_(...) < (...)`** — comparação lexicográfica, eficiente.
- **`limite + 1`** — truque pra saber se há próxima página sem fazer query extra.

### Cursor opaco

O cursor deve ser **opaco** para o cliente (base64 de JSON, ou base64url, ou JWT assinado). Por quê:

- Cliente não deve construir cursor manualmente.
- Permite mudar o schema interno (`{c, id}` virar `{c, id, sort}`) sem quebrar clientes.
- Assinatura (HMAC) evita manipulação maliciosa.

### Limitações do keyset

- **Não há "página N" arbitrária** — só "próxima" e "anterior". Aceite isso na UX.
- **Ordenação fixa** pela query que gerou o cursor. Mudar `order_by` quebra cursores antigos.
- **Filtros dinâmicos** complicam — cursor é válido apenas dentro do mesmo conjunto de filtros.

## Contagem total — evite quando possível

`COUNT(*)` em tabela grande é caro. Em paginação keyset, **não retorne `total`** por padrão.

```python
# Padrão: sem total
return Pagina(itens=itens, proximo_cursor=proximo_cursor)

# Com total quando explicitamente pedido (caro)
if incluir_total:
    total = await session.scalar(
        select(func.count()).select_from(Pedido).where(...mesmos filtros...)
    )
    return Pagina(itens=itens, proximo_cursor=proximo_cursor, total=total)
```

### Alternativas a `COUNT(*)`

- **"tem mais"** boolean — basta saber se existe próxima página (já vem do truque `limite + 1`).
- **Estimativa** — Postgres tem `pg_class.reltuples` (atualizado por ANALYZE) pra estimativa rápida.
- **Materialized view** com count pré-calculado, atualizada periodicamente.
- **Contador denormalizado** em outra tabela, mantido via trigger ou app.

## Limites de tamanho

Sempre limite o tamanho de página:

```python
LIMITE_PADRAO = 20
LIMITE_MAXIMO = 100

limite = min(payload.limite or LIMITE_PADRAO, LIMITE_MAXIMO)
```

Sem limite, cliente pode pedir `?limite=999999` e derrubar o serviço.

## Endpoint exemplo

```python
@router.get("", response_model=Pagina[PedidoResponse])
async def listar(
    session: SessionDep,
    pag: PaginaDep,    # ver 22-fastapi-dependencias.md
) -> Pagina[PedidoResponse]:
    pagina = await pedido_service.listar(session, cursor=pag.cursor, limite=pag.limite)
    return Pagina(
        itens=[PedidoResponse.model_validate(p, from_attributes=True) for p in pagina.itens],
        proximo_cursor=pagina.proximo_cursor,
    )
```

Resposta:

```json
{
  "itens": [...],
  "proximo_cursor": "eyJjIjoiMjAyNi0wNS0wMVQxMDowMDowMCIsImlkIjoxMjM0NX0="
}
```

Cliente pega `proximo_cursor` e envia em `?cursor=<base64>` no próximo request.

## Streaming para exports grandes

Para baixar **tudo** (relatórios, exports), não pagine — use **streaming**:

```python
from fastapi.responses import StreamingResponse

@router.get("/export.csv")
async def exportar(session: SessionDep) -> StreamingResponse:
    async def gerar() -> AsyncIterator[bytes]:
        yield b"id,criado_em,total\n"
        # SQLAlchemy 2.0 — stream em lotes
        async for pedido in (await session.stream_scalars(select(Pedido))):
            yield f"{pedido.id},{pedido.criado_em},{pedido.total}\n".encode()

    return StreamingResponse(gerar(), media_type="text/csv")
```

`stream_scalars()` carrega em **batches do banco** sem materializar tudo em memória.

## Anti-padrões

- ❌ `OFFSET N` com N grande em tabela alta — degradação linear.
- ❌ Cursor não opaco (cliente vê/constrói).
- ❌ Ordenação sem desempate (`order_by(criado_em)` sem `id` como tiebreaker).
- ❌ Cursor sem índice cobrindo a ordenação.
- ❌ `COUNT(*)` em toda página por default.
- ❌ Sem `limite` máximo — cliente pede milhares de registros.
- ❌ Paginação cliente-side (`SELECT *`, depois slice no Python).
- ❌ Misturar offset e keyset na mesma API — escolha um e mantenha.
- ❌ Cursor que codifica filtros + ordenação implicitamente sem validação no recebimento.
