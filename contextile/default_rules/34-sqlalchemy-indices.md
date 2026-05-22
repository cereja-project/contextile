---
apply: off
instructions: Apply when deciding which columns to index, creating composite/partial indexes, writing Alembic migrations for indexes, or diagnosing slow queries.
---

# SQLAlchemy 2.0+ — Índices no Banco

> **Aplica-se quando**: decidindo quais colunas indexar, criando índices compostos/parciais, escrevendo migrations Alembic, ou diagnosticando queries lentas.

## Quando adicionar índice

Adicione índice em colunas que:

1. **Aparecem em `WHERE` frequentemente** — filtros do dia-a-dia.
2. **Aparecem em `JOIN`** — foreign keys quase sempre.
3. **Aparecem em `ORDER BY`** — especialmente para paginação keyset.
4. **Têm restrição `UNIQUE`** — automaticamente indexado.

Não adicione índice em:

- Colunas com **baixa cardinalidade** (boolean, enum de 2-3 valores) — o banco prefere Seq Scan.
- Tabelas pequenas (< ~1.000 linhas) — Seq Scan é mais rápido que usar índice.
- Colunas raramente filtradas (custo de manutenção sem benefício de leitura).

## Foreign keys — sempre indexe

`ForeignKey` **não cria índice automaticamente** em Postgres. Faça explicitamente:

```python
class Pedido(Base):
    __tablename__ = "pedidos"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("clientes.id"),
        index=True,  # ← sempre
    )
```

Sem isso, JOIN com a tabela pai vira Seq Scan; DELETE/UPDATE em `clientes` lock a tabela inteira de `pedidos`.

## Índices compostos — ordem importa

```python
__table_args__ = (
    Index("ix_pedidos_cliente_criado", "cliente_id", "criado_em"),
)
```

A regra: índice composto `(A, B)` é usado em queries que filtram por:

- `A`
- `A AND B`
- **NÃO** apenas `B` (ou usa, mas mal)

**Ordem das colunas**: a mais seletiva primeiro, ou a que aparece em filtro de igualdade antes da que aparece em range/sort.

Exemplo: para a query

```sql
SELECT * FROM pedidos WHERE cliente_id = 42 ORDER BY criado_em DESC LIMIT 20;
```

O índice ideal é `(cliente_id, criado_em)` — primeiro filtra, depois já vem ordenado.

### Para paginação keyset

```python
__table_args__ = (
    # mesma ordem da query: ORDER BY criado_em DESC, id DESC
    Index("ix_pedidos_ordenacao", "criado_em", "id"),
)
```

Sem esse índice, paginação keyset perde a vantagem.

## Índices parciais (Postgres)

Quando a query filtra **sempre** por um valor específico, índice parcial é mais leve:

```python
from sqlalchemy import Index

__table_args__ = (
    Index(
        "ix_pedidos_ativos_criado",
        "criado_em",
        postgresql_where=sa.text("status != 'cancelado'"),
    ),
)
```

Útil quando 90%+ das queries têm o mesmo `WHERE status != 'cancelado'`. Índice fica menor → mais rápido e cacheia melhor.

## Índice único composto

Para restrições de unicidade combinada:

```python
__table_args__ = (
    UniqueConstraint("cliente_id", "produto_id", name="uq_carrinho_cliente_produto"),
)
```

Garante "um produto por cliente no carrinho" no nível do banco. ORM-only não basta — corrida concorrente fura.

## Tipos de índice (Postgres)

- **B-tree** (default) — igualdade, range, ORDER BY. Use em 99% dos casos.
- **Hash** — apenas igualdade. Raramente vale a pena vs B-tree em Postgres moderno.
- **GIN** — busca em arrays, JSONB, full-text:
  ```python
  Index("ix_pedidos_tags", "tags", postgresql_using="gin")
  ```
- **GiST** — geometria, ranges, full-text (alternativa a GIN).
- **BRIN** — tabelas muito grandes com dados naturalmente ordenados (timestamps em append-only). Índice **minúsculo**.

Não use Hash, GIN, GiST, BRIN sem necessidade comprovada — B-tree resolve a maioria.

## Índices em JSONB

Para queries que filtram dentro de JSONB:

```python
__table_args__ = (
    # índice em chave específica
    Index(
        "ix_pedidos_metadata_origem",
        sa.text("(metadata->>'origem')"),
    ),
    # índice GIN para queries genéricas (?, @>, etc.)
    Index("ix_pedidos_metadata_gin", "metadata", postgresql_using="gin"),
)
```

## Criação concorrente em produção

`CREATE INDEX` lock a tabela. Em produção, use **`CREATE INDEX CONCURRENTLY`** (Postgres):

```python
# Em migration Alembic
def upgrade() -> None:
    op.create_index(
        "ix_pedidos_cliente_criado",
        "pedidos",
        ["cliente_id", "criado_em"],
        postgresql_concurrently=True,
    )
```

Mas atenção:

- **Não pode rodar dentro de transação** — Alembic precisa de `with op.get_context().autocommit_block():`.
- **Não falha imediatamente** se índice ficar inválido — verifique no banco após a migration.

```python
def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_pedidos_cliente_criado",
            "pedidos",
            ["cliente_id", "criado_em"],
            postgresql_concurrently=True,
        )
```

## Verificação: EXPLAIN ANALYZE

Toda nova query de alto volume deve ser validada com EXPLAIN:

```sql
EXPLAIN ANALYZE
SELECT * FROM pedidos
WHERE cliente_id = 42
ORDER BY criado_em DESC
LIMIT 20;
```

Procure por:

- **Index Scan** ou **Bitmap Index Scan** = bom.
- **Seq Scan** em tabela grande = ruim (provavelmente falta índice).
- **Sort** após scan = ruim (índice não cobre a ordenação).
- **Filter** descartando muitas linhas = índice ineficiente ou parcial faltando.

## Monitoramento — índices não usados

Periodicamente (mensal/trimestral) verifique índices não usados em Postgres:

```sql
SELECT schemaname, relname, indexrelname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0 AND indexrelname NOT LIKE '%_pkey'
ORDER BY pg_relation_size(indexrelid) DESC;
```

Índice nunca escaneado = peso morto (custo em INSERT/UPDATE sem benefício em SELECT). Considere remover.

## Manutenção

- **Postgres**: `VACUUM` e `ANALYZE` (geralmente automáticos). `REINDEX` raramente — só se índice corrompeu ou após muita atualização.
- **Inchaço** (bloat): se a tabela tem muitos UPDATEs, índices podem inchar — `REINDEX CONCURRENTLY` periódico ajuda.

## Índices em testes

**Não rode testes em SQLite** se a produção é Postgres. Diferenças importantes:

- Tipos de índice (GIN, BRIN, parcial) só existem em Postgres.
- Comportamento de `LIKE`/`ILIKE` com índice difere.
- Constraints CHECK complexas podem não funcionar.

Testes de integração devem usar **Postgres** (via Docker, Testcontainers, etc.).

## Padrão recomendado neste projeto

Em cada model novo:

1. **Toda foreign key** → `index=True`.
2. **Colunas usadas em paginação** → índice composto `(coluna_ordenada, id)`.
3. **Colunas usadas em filtro de listagem** → índice (composto se múltiplos filtros).
4. **Naming**: `ix_<tabela>_<colunas>` (configurado no naming convention do metadata).

## Anti-padrões

- ❌ FK sem `index=True`.
- ❌ Adicionar índice "preventivo" em coluna nunca usada em WHERE/JOIN/ORDER BY.
- ❌ Índice em boolean (`status`, `ativo`) — baixa cardinalidade.
- ❌ Ordem errada em índice composto (coluna menos seletiva primeiro).
- ❌ `CREATE INDEX` (não concorrente) em produção — bloqueia tabela.
- ❌ Migration de índice grande dentro de transação Alembic padrão.
- ❌ Não verificar com EXPLAIN ANALYZE em queries críticas.
- ❌ Testes em SQLite quando prod é Postgres.
- ❌ Manter índices nunca usados (peso morto em escrita).
- ❌ Índice GIN/GiST/BRIN "porque parece avançado" — B-tree resolve 99%.
