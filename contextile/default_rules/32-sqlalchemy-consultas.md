---
apply: by model decision
instructions: Apply when writing SQLAlchemy queries, choosing eager loading strategy for relationships, optimizing query performance, or performing bulk operations.
---

# SQLAlchemy 2.0+ — Consultas e Performance

> **Aplica-se quando**: escrevendo queries, escolhendo estratégia de loading de relacionamentos, otimizando performance, ou fazendo operações em massa.

## API 2.0 — sempre

Use **`select()` + `session.execute()` / `session.scalars()`**. **Nunca** use `session.query()` (API 1.x deprecada).

```python
from sqlalchemy import select

# ✅ 2.0 style
stmt = select(Cliente).where(Cliente.email == email)
result = await session.execute(stmt)
cliente = result.scalar_one_or_none()

# ❌ 1.x style
cliente = session.query(Cliente).filter(Cliente.email == email).first()
```

## `scalars` vs `execute`

Para queries que retornam **um único modelo** (não tupla), use `scalars()` — é mais limpo:

```python
# Modelo único
stmt = select(Cliente).where(Cliente.ativo)
clientes = (await session.scalars(stmt)).all()

# Múltiplas colunas / agregação — use execute()
stmt = select(Cliente.id, func.count(Pedido.id)).join(Pedido).group_by(Cliente.id)
result = await session.execute(stmt)
for cliente_id, total in result:
    ...
```

Métodos úteis em `scalars()`:

- `.all()` — list de objetos.
- `.first()` — primeiro ou `None`.
- `.one()` — exatamente um (erro se 0 ou >1).
- `.one_or_none()` — um ou `None` (erro se >1).

## Get por PK

Para buscar por chave primária, use `session.get` — usa cache de identidade:

```python
# ✅ rápido, usa cache
cliente = await session.get(Cliente, cliente_id)

# ✅ com eager loading
cliente = await session.get(
    Cliente, cliente_id,
    options=[selectinload(Cliente.pedidos)],
)
```

`session.get` evita query se o objeto já está no cache de identidade da sessão.

## Loading strategies — escolha na query

O problema **N+1**: você busca N clientes, depois acessa `cliente.pedidos` em cada um → N queries extras.

```python
# ❌ N+1
clientes = (await session.scalars(select(Cliente))).all()
for c in clientes:
    print(len(c.pedidos))  # uma query por cliente
```

Resolva com **eager loading** na query:

### `selectinload` — padrão para coleções (1:N, N:M)

```python
from sqlalchemy.orm import selectinload

stmt = select(Cliente).options(selectinload(Cliente.pedidos))
clientes = (await session.scalars(stmt)).all()
# 1 query para clientes + 1 query para pedidos (IN com todos os IDs)
```

Faz 2 queries no total — uma para o pai, outra para os filhos com `WHERE id IN (...)`. Performa bem com qualquer N.

### `joinedload` — para 1:1 ou N:1

```python
from sqlalchemy.orm import joinedload

stmt = select(Pedido).options(joinedload(Pedido.cliente))
```

Faz **um JOIN** no SQL. Bom para relacionamentos **muitos-para-um** (cada pedido tem um cliente). **Ruim** para coleções grandes — duplica linhas do pai.

### `selectinload` ou `joinedload` — escolha rápida

| Cardinalidade           | Use            |
| ----------------------- | -------------- |
| 1:1, N:1 (filho → pai)  | `joinedload`   |
| 1:N, N:M (pai → filhos) | `selectinload` |

Em dúvida, `selectinload` é mais seguro — evita explosão cartesiana acidental.

### Loading aninhado

```python
stmt = select(Cliente).options(
    selectinload(Cliente.pedidos).selectinload(Pedido.itens)
)
```

Carrega cliente, depois pedidos, depois itens — 3 queries no total.

### `raiseload` — proibir lazy load acidental

```python
from sqlalchemy.orm import raiseload

stmt = select(Cliente).options(
    selectinload(Cliente.pedidos),
    raiseload("*"),  # qualquer outro lazy load lança erro
)
```

Útil em dev/testes para garantir que todo loading é explícito. Não use em prod (lança em qualquer acesso lazy esquecido).

## Joins explícitos

Para filtrar por atributo de tabela relacionada:

```python
from sqlalchemy.orm import contains_eager

stmt = (
    select(Cliente)
    .join(Cliente.pedidos)
    .where(Pedido.total > 1000)
    .options(contains_eager(Cliente.pedidos))
)
```

`contains_eager` informa ao ORM: "já fiz o JOIN, use as linhas que vieram". Sem isso, ele faz query extra.

## Filtros, ordenação, projeção

```python
from sqlalchemy import select, and_, or_, desc

stmt = (
    select(Cliente)
    .where(
        Cliente.ativo,
        Cliente.criado_em >= data_inicio,           # AND implícito entre args
        or_(Cliente.tipo == "vip", Cliente.tipo == "premium"),
    )
    .order_by(desc(Cliente.criado_em))
    .limit(20)
)
```

`where(a, b, c)` é AND. Para OR, use `or_(...)`. Para combinar AND e OR, `and_()` e `or_()`.

## Projeção parcial — só as colunas que importam

Quando você não precisa da entidade completa, **projete só o necessário**:

```python
# ✅ retorna tuplas (id, nome) — muito mais leve
stmt = select(Cliente.id, Cliente.nome).where(Cliente.ativo)
for cliente_id, nome in await session.execute(stmt):
    ...
```

Útil em listagens grandes onde o response model precisa de poucos campos.

## Agregações

```python
from sqlalchemy import func

stmt = (
    select(
        Cliente.id,
        func.count(Pedido.id).label("total_pedidos"),
        func.sum(Pedido.valor).label("valor_total"),
    )
    .join(Pedido, isouter=True)
    .group_by(Cliente.id)
)
```

`.label("...")` nomeia a coluna no resultado — facilita acessar `.total_pedidos` em vez de índice posicional.

## INSERT em massa

Para muitos registros, use `session.execute(insert(...).values([...]))`:

```python
from sqlalchemy import insert

await session.execute(
    insert(Cliente),
    [
        {"nome": "Ana", "email": "ana@x.com"},
        {"nome": "Bruno", "email": "bruno@x.com"},
        ...
    ],
)
```

Muito mais rápido que `session.add(Cliente(...))` em loop — uma única ida ao banco.

Para upsert (Postgres):

```python
from sqlalchemy.dialects.postgresql import insert as pg_insert

stmt = pg_insert(Cliente).values(...)
stmt = stmt.on_conflict_do_update(
    index_elements=["email"],
    set_={"nome": stmt.excluded.nome},
)
await session.execute(stmt)
```

## UPDATE e DELETE em massa

```python
from sqlalchemy import update, delete

# UPDATE ... WHERE
await session.execute(
    update(Cliente)
    .where(Cliente.criado_em < cutoff)
    .values(ativo=False)
)

# DELETE ... WHERE
await session.execute(
    delete(Cliente).where(Cliente.deletado_em.isnot(None))
)
```

**Atenção**: bulk update/delete **não dispara eventos do ORM** (`@event.listens_for`) e **não atualiza objetos já carregados** na sessão. Se precisar dos hooks, faça loop.

## EXPLAIN no desenvolvimento

Ao escrever query nova com volume esperado, **rode EXPLAIN ANALYZE** na base de dev/staging:

```sql
EXPLAIN ANALYZE
SELECT * FROM clientes WHERE email = 'ana@x.com';
```

Use a saída pra confirmar que está usando índice, não fazendo Seq Scan em tabela grande.

## Echo / log de queries

Em dev, habilite log de SQL:

```python
engine = create_async_engine(url, echo=True)         # imprime todas as queries
# ou via logging
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
```

**Desligue em prod** — performance ruim e logs gigantes.

## Anti-padrões

- ❌ `session.query(...)` — API 1.x deprecada.
- ❌ Acessar `obj.relacionamento` sem ter carregado eager — N+1 silencioso.
- ❌ `joinedload` em relacionamento 1:N grande — explode linhas.
- ❌ `lazy="joined"` no `relationship` em vez de declarar na query.
- ❌ `session.add()` em loop para milhares de registros — use bulk insert.
- ❌ `for c in session.query(Cliente).all(): c.email` quando só precisa do email — use projeção.
- ❌ Query sem `limit()` em listagem.
- ❌ `update`/`delete` em massa esperando que hooks de ORM disparem.
- ❌ Não rodar EXPLAIN em query nova de alto volume.
- ❌ `echo=True` em produção.
