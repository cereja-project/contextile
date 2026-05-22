---
apply: by model decision
instructions: Apply when defining domain entities, DTOs, HTTP request/response schemas, configuration models, or choosing between dataclass, Pydantic, NamedTuple, or dict.
---

# Python — Modelagem de Dados

> **Aplica-se quando**: definindo entidades de domínio, DTOs, schemas de entrada/saída HTTP, configurações, ou decidindo entre `dataclass`, `Pydantic`, `NamedTuple` ou `dict`.

## Árvore de decisão

| Caso de uso                                              | Use                            |
| -------------------------------------------------------- | ------------------------------ |
| Entidade de domínio / value object (interno)             | `@dataclass(frozen, slots)`    |
| Request/Response HTTP (borda da aplicação)               | `pydantic.BaseModel`           |
| Parsing de JSON externo, CSV, env vars                   | `pydantic.BaseModel`           |
| Configuração da aplicação (env vars + defaults)          | `pydantic_settings.BaseSettings` |
| Registro pequeno, imutável, com poucos campos            | `NamedTuple`                   |
| Estado mutável com lógica de domínio rica                | classe normal                  |
| Estrutura genuinamente dinâmica (chaves variáveis)       | `dict[str, X]` tipado          |

**Regra de separação**: Pydantic vive nas **bordas** do sistema (HTTP, fila, parser de arquivo). Núcleo de domínio usa `dataclass`. Não passe `BaseModel` adiante do handler de entrada — converta para o tipo de domínio.

## `@dataclass` — padrão do domínio

Defaults recomendados:

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True, kw_only=True)
class Cliente:
    id: int
    nome: str
    email: str
    tipo: TipoCliente = TipoCliente.COMUM
```

- `frozen=True` — imutável; mutação cria nova instância via `dataclasses.replace`.
- `slots=True` — menos memória, evita atributos não declarados.
- `kw_only=True` — força keyword args, ordem não importa, errado fica óbvio.

### Quando relaxar cada flag

- Desligue `frozen` se o objeto **precisa** mutar (raro em domínio bem desenhado).
- Desligue `slots` se a classe usa `multiple inheritance` complexa ou descritores.
- Desligue `kw_only` em tipos com 1-2 campos óbvios pela ordem.

### Campos com defaults mutáveis

```python
from dataclasses import dataclass, field

@dataclass(frozen=True, slots=True, kw_only=True)
class Pedido:
    id: int
    itens: list[Item] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)
```

**Nunca** `itens: list[Item] = []` direto — repete o bug do mutable default arg.

### Post-init para campos derivados

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class Pedido:
    itens: tuple[Item, ...]
    total: Decimal = field(init=False)

    def __post_init__(self):
        # frozen exige object.__setattr__
        object.__setattr__(self, "total", sum(i.preco for i in self.itens))
```

Se está usando `__post_init__` para muita coisa, provavelmente quer um construtor classmethod (`Pedido.from_itens(...)`).

### Herança em dataclass

Evite. Quando absolutamente necessário, todos os campos do pai devem ter default (limitação de Python):

```python
@dataclass(kw_only=True)
class Base:
    id: int

@dataclass(kw_only=True)
class Filha(Base):
    nome: str
```

`kw_only=True` resolve o problema clássico de ordem de defaults na herança.

## `pydantic.BaseModel` — borda da aplicação

Para validação na entrada/saída do sistema:

```python
from pydantic import BaseModel, ConfigDict, Field, EmailStr

class CriarClienteRequest(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",  # rejeita campos não declarados
        str_strip_whitespace=True,
    )

    nome: str = Field(min_length=2, max_length=100)
    email: EmailStr
    idade: int = Field(ge=0, le=150)
```

### Defaults de `model_config`

- `frozen=True` — imutável após criação (mesma filosofia do dataclass).
- `extra="forbid"` — entrada com campo inesperado falha. **Sempre** para requests; evita aceitar lixo silenciosamente.
- `str_strip_whitespace=True` — remove espaços em strings automaticamente.
- `validate_assignment=True` — se desabilitar `frozen`, valida na atribuição.

### Separe request, domínio e response

```python
# Borda (Pydantic)
class CriarClienteRequest(BaseModel): ...
class ClienteResponse(BaseModel): ...

# Domínio (dataclass)
@dataclass(frozen=True, slots=True, kw_only=True)
class Cliente: ...

# Conversão explícita
def criar_cliente(req: CriarClienteRequest) -> ClienteResponse:
    cliente = Cliente(id=gerar_id(), nome=req.nome, email=req.email, ...)
    repo.salvar(cliente)
    return ClienteResponse.model_validate(cliente, from_attributes=True)
```

Não use a mesma classe para os três papéis — request, entidade e response têm **regras de validação e exposição diferentes**.

### Validadores

```python
from pydantic import field_validator, model_validator

class TransferenciaRequest(BaseModel):
    origem: int
    destino: int
    valor: Decimal

    @field_validator("valor")
    @classmethod
    def valor_positivo(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("valor deve ser positivo")
        return v

    @model_validator(mode="after")
    def contas_diferentes(self) -> Self:
        if self.origem == self.destino:
            raise ValueError("origem e destino devem ser diferentes")
        return self
```

### Métodos de uso (Pydantic v2)

- `Modelo.model_validate(data)` para criar a partir de dict/objeto.
- `instancia.model_dump()` para serializar para dict.
- `instancia.model_dump_json()` para JSON.
- `Modelo.model_json_schema()` para schema (útil em OpenAPI).

**Nunca** use o estilo v1: `.dict()`, `.parse_obj()`, `.json()`. São deprecated.

## `pydantic_settings.BaseSettings` — configuração

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str
    redis_url: str = "redis://localhost:6379"
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR)$")
    debug: bool = False
```

- Carrega de variáveis de ambiente e `.env`.
- Tipos checados no boot — config inválida quebra o app no startup, não no primeiro request.
- Use **singleton via `lru_cache`** no entrypoint:
  ```python
  from functools import lru_cache

  @lru_cache
  def get_settings() -> Settings:
      return Settings()
  ```

## Enums para estados finitos

Quando um campo só aceita um conjunto fixo de valores, **use enum**, não string.

```python
from enum import StrEnum, auto

class StatusPedido(StrEnum):
    RASCUNHO = "rascunho"
    CONFIRMADO = "confirmado"
    PAGO = "pago"
    ENVIADO = "enviado"
    ENTREGUE = "entregue"
    CANCELADO = "cancelado"
```

- `StrEnum` (3.11+) — valor é a própria string, serializa direto.
- `IntEnum` — valor numérico (útil para códigos de erro).
- `auto()` — quando o valor é arbitrário e o nome basta.

### `Literal` vs `Enum`

```python
# ✅ Literal — quando os valores aparecem em poucos lugares e não têm comportamento associado
def gerar_relatorio(formato: Literal["pdf", "csv", "xlsx"]) -> bytes: ...

# ✅ Enum — quando é um conceito de domínio reutilizado, com comparações, ordenação, ou serialização
status: StatusPedido = StatusPedido.CONFIRMADO
```

Regra: se o valor vai aparecer em mais de 2-3 lugares, vira enum.

## `NamedTuple` — quando faz sentido

Para registros pequenos, imutáveis, posicionais ou não:

```python
from typing import NamedTuple

class Coordenada(NamedTuple):
    latitude: float
    longitude: float
```

Vantagens: imutável, mais leve que dataclass, desempacotável (`lat, lng = coord`).

Limitações: sem `__post_init__`, sem defaults complexos, sem métodos práticos. Para qualquer coisa além de "dois ou três campos numéricos", prefira `dataclass`.

## `dict` tipado — quando o schema é genuinamente dinâmico

```python
metadata: dict[str, str | int]  # ok quando chaves variam
```

Mas se você consulta sempre as mesmas chaves (`metadata["criado_por"]`), é um dataclass disfarçado — converta.

`TypedDict` é alternativa quando precisa de chaves fixas mas o objeto vem de JSON externo e a conversão custa:

```python
from typing import TypedDict

class UsuarioDict(TypedDict):
    id: int
    nome: str
```

Em quase todos os casos, prefira `BaseModel` ou `dataclass` ao `TypedDict`.
