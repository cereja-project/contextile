---
apply: by model decision
instructions:  Apply when defining SQLAlchemy ORM models, configuring tables, relationships, mixins, or organizing the persistence 
---

# SQLAlchemy 2.0+ — Mapeamento e Estrutura

> **Aplica-se quando**: definindo modelos ORM, configurando tabelas, relacionamentos, mixins, ou organizando a camada de persistência com SQLAlchemy 2.0+.

## Sintaxe 2.0 — sempre

Use **`DeclarativeBase` + `Mapped[X]` + `mapped_column`**. Não use estilo 1.x (`Column`, `declarative_base()` function, `Query`).

```python
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, String, Numeric, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    """Base de todos os modelos ORM."""

class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )

    pedidos: Mapped[list["Pedido"]] = relationship(back_populates="cliente")
```

Vantagens da sintaxe 2.0:

- **Type-safe**: `Mapped[str]` é checado por mypy/pyright. Atributos não declarados quebram.
- **Nullability vem do tipo**: `Mapped[str]` é NOT NULL; `Mapped[str | None]` permite NULL.
- **Sem duplicação**: tipo declarado uma vez, no `Mapped[...]`.

## Nullability vem do `Mapped[...]`

```python
nome: Mapped[str]              # NOT NULL
apelido: Mapped[str | None]    # nullable
```

Não precisa de `nullable=True/False` em `mapped_column` — vem da anotação. Se houver conflito, o tipo vence.

## `mapped_column` — quando usar

`mapped_column` é opcional quando só precisa do tipo:

```python
# ✅ ambos válidos
nome: Mapped[str] = mapped_column(String(100))
descricao: Mapped[str]   # tipo SQL inferido (Text/Varchar dependendo do dialeto)
```

Use `mapped_column` quando precisa de:

- Tipo SQL específico (`String(100)`, `Numeric(12, 2)`).
- Constraints (`unique=True`, `index=True`, `primary_key=True`).
- Defaults (`default=`, `server_default=`).
- Foreign keys (`ForeignKey("...")`).

## Defaults — Python vs servidor

```python
# default Python — calculado no app
criado_em: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

# server_default — calculado pelo banco (recomendado para timestamps)
criado_em: Mapped[datetime] = mapped_column(server_default=func.now())
```

Prefira **`server_default`** para:

- Timestamps (`now()`, `current_timestamp`).
- UUIDs gerados pelo banco.
- Sequencias.

Vantagens: consistência entre apps que tocam o banco, valores corretos em bulk insert no SQL puro, sem desvio de relógio entre instâncias.

## Relacionamentos

```python
from sqlalchemy.orm import relationship

class Pedido(Base):
    __tablename__ = "pedidos"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"))

    cliente: Mapped["Cliente"] = relationship(back_populates="pedidos")
    itens: Mapped[list["ItemPedido"]] = relationship(
        back_populates="pedido",
        cascade="all, delete-orphan",
    )
```

Regras:

- **Sempre** declare ambos os lados com `back_populates` — não use `backref` (mágica implícita).
- **Sempre** declare o tipo via `Mapped[...]` — relacionamentos sem `Mapped` não são checados.
- Use **forward reference** (string) para tipos definidos depois (`Mapped["ItemPedido"]`).
- **`cascade="all, delete-orphan"`** apenas em relação composição (pai dono dos filhos). Para associação simples, não use cascade.

### Estratégia de loading — declarada na consulta, não no modelo

```python
# ❌ lazy/joined/etc fixo no modelo limita callers
pedidos: Mapped[list["Pedido"]] = relationship(lazy="joined")

# ✅ default lazy (select), cada query escolhe sua estratégia
pedidos: Mapped[list["Pedido"]] = relationship(back_populates="cliente")
```

Estratégias de loading (joinedload, selectinload) são decididas na **query**, não no modelo. Mais flexível e evita N+1 acidental. Detalhes em `32-sqlalchemy-consultas.md`.

## Foreign keys

```python
cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"))

# com ação ON DELETE
cliente_id: Mapped[int] = mapped_column(
    ForeignKey("clientes.id", ondelete="CASCADE"),
)
```

- `ondelete="CASCADE"` — apaga em cascata no banco.
- `ondelete="SET NULL"` — exige `Mapped[int | None]`.
- `ondelete="RESTRICT"` — impede deleção do pai se houver filhos (default).

Garanta que **ON DELETE no banco bate com `cascade` no ORM**. Inconsistência vira bug intermitente.

## `__table_args__` — constraints e índices

Para constraints e índices que envolvem múltiplas colunas:

```python
from sqlalchemy import Index, UniqueConstraint, CheckConstraint

class ItemPedido(Base):
    __tablename__ = "item_pedido"

    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id"), primary_key=True)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.id"), primary_key=True)
    quantidade: Mapped[int]
    preco: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    __table_args__ = (
        UniqueConstraint("pedido_id", "produto_id", name="uq_item_pedido_produto"),
        CheckConstraint("quantidade > 0", name="ck_quantidade_positiva"),
        Index("ix_item_pedido_produto", "produto_id"),
    )
```

**Sempre nomeie constraints/índices** (`uq_*`, `ck_*`, `ix_*`, `fk_*`) — facilita migrations e debugging. Configure naming convention no metadata para automatizar:

```python
from sqlalchemy import MetaData

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
```

## Mixins reutilizáveis

```python
from sqlalchemy.orm import declared_attr

class TimestampMixin:
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )

class SoftDeleteMixin:
    deletado_em: Mapped[datetime | None] = mapped_column(default=None)

class Cliente(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "clientes"
    ...
```

Mixins ficam **antes** de `Base` na ordem de herança (segue MRO do Python).

## Tipos SQL específicos

| Python type        | mapped_column                                             |
| ------------------ | --------------------------------------------------------- |
| `int`              | `Mapped[int]` (Integer) ou `BigInteger` para IDs grandes  |
| `str`              | `mapped_column(String(N))` — sempre limite o tamanho      |
| `Decimal`          | `mapped_column(Numeric(precision, scale))`                |
| `datetime` aware   | `mapped_column(DateTime(timezone=True))`                  |
| `date`             | `Mapped[date]` (Date)                                     |
| `bool`             | `Mapped[bool]` (Boolean)                                  |
| `bytes`            | `Mapped[bytes]` (LargeBinary)                             |
| `dict[str, ...]`   | `mapped_column(JSONB)` (Postgres) ou `JSON` (genérico)    |
| `UUID`             | `mapped_column(UUID(as_uuid=True))`                       |
| Enum               | `mapped_column(Enum(MeuEnum))`                            |

**Nunca** use `DateTime` sem `timezone=True` em colunas que guardam tempo. Time-zone-naive em banco é fonte certeira de bugs.

## Modelo ORM vs entidade de domínio

Em projetos pequenos, **modelo ORM serve como entidade de domínio**. Em projetos com regras de negócio complexas, separe:

```
dominio/
└── pedido.py          # @dataclass Pedido (regras puras)
infra/
└── persistencia/
    └── pedido_orm.py  # class PedidoORM(Base) (ORM)
    └── repository.py  # mapeia ORM ↔ dataclass
```

Decida no início do projeto. Mudar depois é caro.

## Anti-padrões

- ❌ Sintaxe 1.x (`Column`, `declarative_base()` function, `Query`).
- ❌ Relacionamento sem `Mapped[...]` — perde checagem de tipos.
- ❌ `backref=` em vez de `back_populates=` — esconde a outra ponta.
- ❌ `nullable=True/False` em `mapped_column` quando `Mapped[X | None]` já diz.
- ❌ `lazy="joined"` ou `"selectin"` fixo no `relationship`.
- ❌ `cascade="all, delete-orphan"` em relação não-composição.
- ❌ Tabela sem `__tablename__` explícito.
- ❌ Constraint/índice sem nome (ferra migrations).
- ❌ `String` sem tamanho em coluna texto curto.
- ❌ `DateTime` sem `timezone=True`.
