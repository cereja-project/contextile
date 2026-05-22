# FastAPI — Tratamento de Erros

> **Aplica-se quando**: tratando erros em endpoints, configurando exception handlers, escolhendo status codes HTTP, ou modelando respostas de erro.

> Complementa: `14-python-erros.md` (regras gerais de exceções em Python).

## Princípio: erros de domínio ≠ erros HTTP

A regra que organiza tudo:

- **Service/domínio** levanta exceções **do domínio** (`PedidoNaoEncontrado`, `SaldoInsuficiente`).
- **Handler/dependência** converte para `HTTPException` ou, melhor, **um `exception_handler` global** faz a conversão.

```python
# ❌ service acoplado a HTTP
def buscar(id: int) -> Pedido:
    pedido = repo.find(id)
    if pedido is None:
        raise HTTPException(status_code=404, detail="não encontrado")
    return pedido

# ✅ service de domínio
def buscar(id: int) -> Pedido:
    pedido = repo.find(id)
    if pedido is None:
        raise PedidoNaoEncontrado(id)
    return pedido
```

Domínio sem dependência de FastAPI é testável fora do contexto HTTP e reusável em workers, CLIs, etc.

## Exception handlers globais

Mapeie exceções de domínio para status code uma vez, no boot:

```python
# api/errors.py
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from meu_app.dominio.erros import (
    AppError,
    NaoEncontrado,
    RegraDeNegocioViolada,
    AcessoNegado,
)

class ErrorResponse(BaseModel):
    erro: str
    mensagem: str
    detalhes: dict | None = None

def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(NaoEncontrado)
    async def _nao_encontrado(_: Request, exc: NaoEncontrado) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ErrorResponse(erro=type(exc).__name__, mensagem=str(exc)).model_dump(),
        )

    @app.exception_handler(RegraDeNegocioViolada)
    async def _regra(_: Request, exc: RegraDeNegocioViolada) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=ErrorResponse(erro=type(exc).__name__, mensagem=str(exc)).model_dump(),
        )

    @app.exception_handler(AcessoNegado)
    async def _acesso(_: Request, exc: AcessoNegado) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=ErrorResponse(erro=type(exc).__name__, mensagem=str(exc)).model_dump(),
        )

    @app.exception_handler(AppError)  # base — fallback genérico
    async def _app(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(erro=type(exc).__name__, mensagem=str(exc)).model_dump(),
        )
```

Registre no `create_app`:

```python
def create_app(...) -> FastAPI:
    app = FastAPI(...)
    register_exception_handlers(app)
    ...
```

Ordem importa apenas para a especificidade: handlers mais específicos primeiro, base por último.

## Status codes corretos

Padrão mínimo:

| Código | Quando                                                                          |
| ------ | ------------------------------------------------------------------------------- |
| 200    | GET com sucesso; PUT/PATCH que retornam o recurso atualizado.                  |
| 201    | POST que **cria** um recurso. Retorne o recurso criado.                         |
| 202    | POST/PUT aceito para processamento assíncrono.                                  |
| 204    | DELETE com sucesso; PUT/PATCH sem retorno de corpo.                             |
| 400    | Erro genérico do cliente. **Evite** — prefira código mais específico.           |
| 401    | Não autenticado (token ausente/inválido). Inclua `WWW-Authenticate`.            |
| 403    | Autenticado mas sem permissão.                                                  |
| 404    | Recurso não existe (ou usuário não tem permissão de saber que existe).         |
| 409    | Conflito com o estado atual (recurso já existe, operação não aplicável).        |
| 422    | Validação falhou (Pydantic gera automaticamente).                               |
| 429    | Rate limit excedido.                                                            |
| 500    | Erro inesperado do servidor. **Nunca** intencional — bug.                       |
| 503    | Dependência indisponível (DB down, serviço externo fora).                       |

**Nunca** retorne 200 com `{"erro": "..."}`. Use o código HTTP correto.

## Erro de validação — 422 automático

`ValidationError` do Pydantic já vira 422 com estrutura padrão do FastAPI:

```json
{
  "detail": [
    {"type": "missing", "loc": ["body", "email"], "msg": "Field required", "input": {}}
  ]
}
```

Para customizar o formato:

```python
from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "erro": "ValidationError",
            "mensagem": "dados inválidos",
            "detalhes": exc.errors(),
        },
    )
```

## `HTTPException` — quando ainda usar

`HTTPException` é apropriado **na borda** quando não vale criar exceção de domínio:

- Autenticação falhou no parser de token.
- Header obrigatório ausente.
- Rate limit no middleware.

Para tudo que é regra de negócio, prefira **exceção de domínio + handler**.

```python
# ok — borda HTTP
if not token:
    raise HTTPException(status_code=401, detail="token ausente")

# ❌ regra de negócio na borda
if pedido.status != StatusPedido.RASCUNHO:
    raise HTTPException(status_code=409, detail="pedido já finalizado")

# ✅
raise PedidoJaFinalizado(pedido.id)
```

## Nunca vazar internos

Erros não tratados (`Exception` não capturada) devem virar **500 genérico**, sem stack trace na resposta:

```python
@app.exception_handler(Exception)
async def _fallback(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("erro não tratado em %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"erro": "InternalServerError", "mensagem": "erro interno"},
    )
```

Stack trace **vai pro log**, **não pro cliente**. Em dev, retornar mais detalhes é aceitável; em prod, jamais.

## Resposta de erro padronizada

Use **um schema único** para erros em todo o app:

```python
class ErrorResponse(BaseModel):
    erro: str         # tipo/código curto (PedidoNaoEncontrado, ValidationError)
    mensagem: str     # legível por humano, em português
    detalhes: dict | None = None  # opcional, para validação ou debug
```

Documente esse schema no OpenAPI:

```python
@router.get(
    "/{id}",
    response_model=ClienteResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Cliente não encontrado"},
        403: {"model": ErrorResponse, "description": "Acesso negado"},
    },
)
async def buscar(id: int, ...) -> ClienteResponse: ...
```

Consumidores da API conseguem gerar clientes tipados que tratam erros corretamente.

## Logging de erros

Em `exception_handler`, log com contexto suficiente:

```python
@app.exception_handler(AppError)
async def _app(request: Request, exc: AppError) -> JSONResponse:
    logger.warning(
        "erro de aplicação: %s",
        type(exc).__name__,
        extra={"path": request.url.path, "method": request.method, "exc": str(exc)},
    )
    ...
```

Para 5xx, use `logger.exception(...)` (inclui traceback). Para 4xx, `logger.warning` ou `info` — não são bugs, são uso normal.

## Anti-padrões

- ❌ `HTTPException` levantada de dentro do service de domínio.
- ❌ Status code 200 com payload `{"erro": "..."}`.
- ❌ `except Exception: raise HTTPException(500, detail=str(exc))` — vaza implementação.
- ❌ Resposta de erro com schema inconsistente entre endpoints.
- ❌ 500 silencioso (sem log) — bug sem investigação possível.
- ❌ Status code 400 genérico quando há código mais específico (404, 409, 422).
- ❌ Sem handler de fallback (`@app.exception_handler(Exception)`) — exceção não capturada vira 500 padrão do Starlette sem log estruturado.
- ❌ Logar payload completo em handler de erro (pode conter dados sensíveis).
