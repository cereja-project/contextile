---
apply: by model decision
instructions: Apply when writing function signatures, declaring types, creating type aliases, generics, or Protocols in Python.
---

# Python — Type Hints (3.12+)

> **Aplica-se quando**: escrevendo assinaturas de funções/métodos, declarando atributos, criando type aliases, generics, protocolos ou ABCs.

## Regra geral

- **Type hints são obrigatórios** em toda função/método público (sem `_` prefix), incluindo retornos.
- Em funções privadas, são fortemente recomendados — só omita em casos triviais óbvios.
- Atributos de classes públicas têm type hints (preferencialmente via `dataclass`, `Mapped[...]`, ou anotação direta).
- Use checagem estática (`mypy` ou `pyright`) em modo estrito no CI.

## Sintaxe moderna (3.12+)

### Use builtins, não `typing.List`/`Dict`/etc.

```python
# ✅ Python 3.9+
def normalizar(nomes: list[str]) -> dict[str, int]: ...

# ❌ Estilo legado
from typing import List, Dict
def normalizar(nomes: List[str]) -> Dict[str, int]: ...
```

### Use `X | None`, não `Optional[X]`

```python
# ✅ Python 3.10+
def buscar(id: int) -> Cliente | None: ...

# ❌ Estilo legado
from typing import Optional
def buscar(id: int) -> Optional[Cliente]: ...
```

### Use `X | Y`, não `Union[X, Y]`

```python
# ✅
def parse(valor: str | bytes) -> dict[str, int]: ...

# ❌
def parse(valor: Union[str, bytes]) -> Dict[str, int]: ...
```

### Type aliases com `type` (PEP 695, 3.12+)

```python
# ✅ Python 3.12+
type UsuarioId = int
type JsonDict = dict[str, "JsonValue"]
type JsonValue = str | int | float | bool | None | list["JsonValue"] | JsonDict

# ❌ Estilo legado
from typing import TypeAlias
UsuarioId: TypeAlias = int
```

### Generics com sintaxe nova (PEP 695, 3.12+)

```python
# ✅ Python 3.12+
def primeiro[T](items: list[T]) -> T | None:
    return items[0] if items else None

class Cache[K, V]:
    def get(self, key: K) -> V | None: ...
    def set(self, key: K, value: V) -> None: ...

# ❌ Estilo legado
from typing import TypeVar, Generic
T = TypeVar("T")
def primeiro(items: list[T]) -> T | None: ...
```

### `Self` para retornar o próprio tipo

```python
from typing import Self

class QueryBuilder:
    def where(self, **filters) -> Self:
        self._filters.update(filters)
        return self
```

## `Protocol` para duck typing estruturado

Prefira `Protocol` a ABC quando você só precisa que algo "tenha o método X". É mais Pythônico, não exige herança.

```python
from typing import Protocol

class Notificador(Protocol):
    def enviar(self, destinatario: str, mensagem: str) -> None: ...

def avisar_cliente(notif: Notificador, cliente: Cliente) -> None:
    notif.enviar(cliente.email, "Pedido confirmado")
    # Qualquer classe com .enviar(str, str) -> None funciona — sem herança.
```

ABCs (`abc.ABC`) ficam para casos de **hierarquia real de tipos** com identidade compartilhada (ex: `PagamentoMethod` com subclasses Cartao, Pix, Boleto).

## Imutabilidade no tipo

```python
from collections.abc import Sequence, Mapping

# ✅ aceita list, tuple — não muta
def total(itens: Sequence[Item]) -> Decimal: ...

# ❌ exige list — limita callers desnecessariamente
def total(itens: list[Item]) -> Decimal: ...
```

Para argumentos, prefira **interfaces abstratas** (`Sequence`, `Mapping`, `Iterable`). Para retornos, prefira **tipos concretos** (`list`, `dict`) — fica claro o que o caller pode fazer.

## Evite `Any`

`Any` desliga a verificação de tipo e contamina o que toca. Alternativas:

- `object` para "qualquer coisa, mas o caller precisa fazer cast/check".
- `Unknown` (via `typing.cast` ou pyright) para parsers de entrada externa.
- Generic com `T` quando o tipo importa mas é parametrizado.

`Any` é aceitável em **boundary** de bibliotecas sem tipos, e ali deve ser convertido logo:

```python
def parse_resposta(payload: Any) -> Cliente:  # payload veio de lib sem tipo
    return Cliente.model_validate(payload)
```

## Anotações em variáveis

Anote quando o tipo não é óbvio pelo lado direito:

```python
clientes: list[Cliente] = []           # ✅ tipo ambíguo (lista vazia)
total: Decimal = Decimal("0")          # ✅ ajuda a IDE
nome = "Ana"                            # ✅ óbvio, dispensa anotação
pedidos = repo.listar()                 # ✅ tipo vem do retorno tipado
```

## `cast` é cheiro de problema

`typing.cast(X, valor)` apenas convence o type checker, não converte nada em runtime. Use só quando:

1. Você sabe mais que o type checker (ex: depois de `isinstance` em árvore complexa).
2. Bibliotecas externas têm tipos imprecisos.

Cada `cast` deve vir com **comentário explicando por quê**.

## `# type: ignore` requer justificativa

```python
# ✅
result = lib_sem_tipos.parse(data)  # type: ignore[no-untyped-call]

# ✅ ainda melhor
result = lib_sem_tipos.parse(data)  # type: ignore[no-untyped-call]  # lib X não tem stubs
```

Nunca use `# type: ignore` sem o código de erro específico — esconde erros futuros.
