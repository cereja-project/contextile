# FastAPI — Schemas (Pydantic v2)

> **Aplica-se quando**: definindo schemas de request/response, validando entrada HTTP, estruturando saída de endpoints, ou configurando documentação OpenAPI gerada.

> Complementa: `17-python-modelagem.md` (regras gerais de Pydantic).

## Separação obrigatória

Para cada recurso, **três schemas distintos** quando há diferença entre entrada e saída:

```python
# schemas/cliente.py
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class ClienteBase(BaseModel):
    """Campos compartilhados entre create/update/response."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    nome: str = Field(min_length=2, max_length=100)
    email: EmailStr

class ClienteCreate(ClienteBase):
    """Entrada para POST /clientes."""
    senha: str = Field(min_length=8, max_length=72)

class ClienteUpdate(BaseModel):
    """Entrada para PATCH /clientes/{id} — todos os campos opcionais."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    nome: str | None = Field(default=None, min_length=2, max_length=100)
    email: EmailStr | None = None

class ClienteResponse(ClienteBase):
    """Saída — sem senha, com campos gerados pelo servidor."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    criado_em: datetime
    atualizado_em: datetime
```

Regras:

- **Nunca** use a mesma classe para entrada e saída. Senha vai na entrada, ID na saída.
- **`extra="forbid"`** em todos os requests — rejeita campos não declarados (evita aceitar lixo silenciosamente).
- **`from_attributes=True`** nos response models — permite `Response.model_validate(orm_obj)`.
- **PATCH** usa schema com todos os campos `| None` e default `None` — diferencia "não enviado" de "enviado como null".

## `response_model` em endpoints

Sempre declare `response_model` (mesmo quando o handler retorna o tipo correto):

```python
@router.get("/{cliente_id}", response_model=ClienteResponse)
async def buscar_cliente(cliente_id: int, session: SessionDep) -> ClienteResponse:
    cliente = await cliente_service.buscar(session, cliente_id)
    return ClienteResponse.model_validate(cliente, from_attributes=True)
```

Por que duplicar tipo no `response_model` E no retorno:

- `response_model` é o que vai pro OpenAPI e filtra a saída (remove campos não declarados).
- Retorno tipado ajuda o type checker e a IDE.

## Converter entidade de domínio para response

```python
@router.get("", response_model=list[ClienteResponse])
async def listar(session: SessionDep) -> list[ClienteResponse]:
    clientes = await cliente_service.listar(session)
    return [ClienteResponse.model_validate(c, from_attributes=True) for c in clientes]
```

`from_attributes=True` no `model_config` permite ler de atributos (ORM, dataclass) em vez de só dict.

## Paginação — schema padronizado

```python
from typing import Generic, TypeVar

T = TypeVar("T")

class Pagina(BaseModel, Generic[T]):
    """Resposta paginada genérica."""
    itens: list[T]
    proximo_cursor: str | None = None
    total: int | None = None  # opcional — só se contar for barato
```

Em Python 3.12+, prefira a sintaxe nova:

```python
class Pagina[T](BaseModel):
    itens: list[T]
    proximo_cursor: str | None = None
    total: int | None = None
```

Uso:

```python
@router.get("", response_model=Pagina[ClienteResponse])
async def listar(...) -> Pagina[ClienteResponse]: ...
```

Estratégias de paginação ficam em `33-sqlalchemy-paginacao.md`. Aqui é só o **shape** da resposta.

## Validação além dos tipos

Use `Field` para limites e padrões, `field_validator`/`model_validator` para regras compostas:

```python
from pydantic import field_validator, model_validator
from typing import Self

class TransferenciaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origem: int = Field(gt=0)
    destino: int = Field(gt=0)
    valor: Decimal = Field(gt=Decimal("0"), max_digits=12, decimal_places=2)
    descricao: str = Field(default="", max_length=255)

    @model_validator(mode="after")
    def contas_diferentes(self) -> Self:
        if self.origem == self.destino:
            raise ValueError("origem e destino devem ser diferentes")
        return self
```

A `ValidationError` resultante vira **422 Unprocessable Entity** automaticamente, com erros estruturados.

## Examples no OpenAPI

```python
class ClienteCreate(BaseModel):
    nome: str = Field(examples=["Ana Silva"])
    email: EmailStr = Field(examples=["ana@exemplo.com"])
```

Para exemplo de objeto inteiro:

```python
class ClienteCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"nome": "Ana Silva", "email": "ana@exemplo.com", "senha": "senha_forte_123"},
            ]
        }
    )
    ...
```

Exemplos no Swagger ajudam consumidores da API.

## Tipos úteis do Pydantic

- `EmailStr` — valida e-mail (`pydantic[email]`).
- `HttpUrl`, `AnyUrl` — URLs.
- `SecretStr` — esconde valor no log/repr (use para senhas em modelos intermediários).
- `UUID4` — UUIDs versão 4.
- `Json` — string que é JSON parseado automaticamente.
- `PositiveInt`, `NonNegativeInt`, `PositiveFloat` — atalhos.

## `model_dump_json` vs `model_dump`

- `model_dump_json()` — produz string JSON. Use no log estruturado ou ao serializar para fila.
- `model_dump(mode="json")` — produz dict com valores JSON-compatíveis (datetime → str, Decimal → str). Use quando precisa transformar antes de serializar.
- `model_dump()` (default) — produz dict com tipos Python (datetime, Decimal). Use para passar para outras funções Python.

## Datas e tempos

Use `datetime` aware (com timezone), nunca naive:

```python
from datetime import datetime, UTC

class EventoCreate(BaseModel):
    ocorreu_em: datetime  # Pydantic exige ISO 8601 com TZ se o tipo for aware
```

Configure projeto pra usar UTC internamente; converta para o fuso do cliente apenas na borda de apresentação.

## Anti-padrões

- ❌ Mesma classe para request e response.
- ❌ Sem `extra="forbid"` em requests — aceita lixo.
- ❌ `model_config` em estilo Pydantic v1 (`class Config: ...`). Use `ConfigDict`.
- ❌ Métodos v1 (`.dict()`, `.json()`, `parse_obj`, `from_orm`). Use `model_dump`, `model_dump_json`, `model_validate`.
- ❌ `response_model` ausente em endpoints públicos.
- ❌ Retornar entidade de domínio direto sem converter para Response schema.
- ❌ Senha/token no response model (mesmo "por engano").
- ❌ Schema gigante de 30 campos. Quebre por contexto (endereço, contato, etc.).
- ❌ `datetime` naive em requests/responses.
