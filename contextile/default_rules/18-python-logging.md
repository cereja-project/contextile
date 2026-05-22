---
apply: by model decision
instructions: Apply when emitting logs, configuring logging, choosing log levels, or handling sensitive data in log records.
---

# Python — Logging

> **Aplica-se quando**: emitindo logs, configurando logging, decidindo nível de log, ou tratando informações sensíveis em registros.

## Regra fundamental

**Nunca use `print()` em código de aplicação.** Use o módulo `logging` da stdlib. `print` é aceitável apenas em scripts CLI cuja saída é o produto final, ou em ferramentas de debug temporárias.

## Logger por módulo

Em cada módulo:

```python
import logging

logger = logging.getLogger(__name__)
```

- `__name__` cria hierarquia automática (`meu_app.dominio.pedido`).
- **Nunca** use `logging.info(...)` direto (root logger).
- **Nunca** crie logger global no `__init__.py`.

## Níveis e quando usar

| Nível       | Quando                                                                          |
| ----------- | ------------------------------------------------------------------------------- |
| `DEBUG`     | Detalhes para investigação (valores intermediários, fluxo). Verboso, desligado em prod. |
| `INFO`      | Eventos normais e marcos relevantes (request recebido, job iniciado, configuração carregada). |
| `WARNING`   | Algo inesperado mas recuperável (retry, fallback, deprecation usada). |
| `ERROR`     | Operação falhou; aplicação continua. Sempre com `exc_info` ou via `logger.exception`. |
| `CRITICAL`  | Falha grave; aplicação pode não continuar (falha em startup, perda de conexão essencial). |

Não invente níveis intermediários. Não use `WARNING` para "info importante" — vira ruído.

## Formato das mensagens

Use **placeholders + args**, não f-strings na mensagem:

```python
# ✅ formatação lazy (só formata se o nível estiver ativo)
logger.info("usuário %s criou pedido %s", user_id, pedido_id)

# ❌ f-string — formata sempre, ignora extras estruturados
logger.info(f"usuário {user_id} criou pedido {pedido_id}")
```

Vantagens do estilo lazy:

1. **Performance** — se DEBUG está desligado, `logger.debug("dump: %s", repr(obj))` não chama `repr`.
2. **Parsers estruturados** capturam os args separadamente (`user_id`, `pedido_id` viram campos no log JSON).
3. **Agregadores** (Sentry, Datadog) agrupam logs pelo template, não pela mensagem renderizada.

## Logging de exceção

Dentro de `except`:

```python
try:
    processar(pedido_id)
except IntegracaoError:
    logger.exception("falha ao processar pedido %s", pedido_id)
    raise
```

`logger.exception(...)` automaticamente inclui traceback. Equivale a `logger.error(..., exc_info=True)`.

Fora de `except`:

```python
logger.error("falha ao processar pedido %s", pedido_id, exc_info=erro_capturado)
```

**Nunca** apenas `logger.error(str(e))` — perde o traceback.

## Contexto estruturado

Sempre que possível, anexe dados estruturados via `extra`:

```python
logger.info(
    "pedido finalizado",
    extra={"pedido_id": pedido.id, "cliente_id": pedido.cliente_id, "total": str(pedido.total)},
)
```

Em handlers estruturados (JSON), `extra` vira campos top-level no log — pesquisáveis e agregáveis.

### Correlação de requisições

Em apps com requisições concorrentes (HTTP, workers), use **`contextvars`** para propagar IDs de correlação sem passar parâmetros:

```python
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

# middleware HTTP define no início de cada request
request_id_var.set(request.headers.get("X-Request-ID", str(uuid4())))

# qualquer logger no contexto pode ler
logger.info("processando", extra={"request_id": request_id_var.get()})
```

Para async, `contextvars` propaga corretamente entre `await` (diferente de `threading.local`).

## `structlog` — recomendado para apps sérias

Para logs estruturados em produção, `structlog` é mais ergonômico que `logging` puro:

```python
import structlog

logger = structlog.get_logger()

logger.info("pedido finalizado", pedido_id=pedido.id, cliente_id=pedido.cliente_id, total=pedido.total)
```

Configure no entrypoint para emitir JSON em produção e formato humano em dev:

```python
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer() if PROD else structlog.dev.ConsoleRenderer(),
    ],
)
```

Se o projeto não usa `structlog`, mantenha-se em `logging` da stdlib com `python-json-logger` para JSON.

## Configuração centralizada

Configure logging **uma vez** no entrypoint da aplicação (`main.py`, `app.py`). Nunca em módulos importados.

```python
# main.py
import logging.config

logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {"class": "pythonjsonlogger.jsonlogger.JsonFormatter"},
    },
    "handlers": {
        "stdout": {"class": "logging.StreamHandler", "formatter": "json"},
    },
    "root": {"level": "INFO", "handlers": ["stdout"]},
    "loggers": {
        "meu_app": {"level": "DEBUG"},
        "sqlalchemy.engine": {"level": "WARNING"},
    },
})
```

Aplicações containerizadas devem logar para **stdout/stderr**, nunca para arquivo — orquestrador captura.

## O que NÃO logar

- **Secrets**: senhas, tokens, chaves API, JWTs completos, cookies de sessão. Mesmo em DEBUG.
- **PII completa**: e-mail, CPF, telefone — mascarar (`ana@***.com`, `***.***.***-12`).
- **Bodies inteiros de request** em INFO+ (podem conter dados sensíveis). Em DEBUG, com cuidado.
- **Dados de cartão**: mesmo mascarados, melhor não passar perto.
- **Stack traces de bibliotecas** que possam expor caminhos internos sensíveis em mensagens de erro de usuário.

Configure um redactor (em `structlog.processors` ou filtro de `logging`) para mascarar automaticamente padrões conhecidos.

## Anti-padrões

- ❌ `print()` em código de aplicação.
- ❌ `logger.info(f"...{var}")` em vez de `logger.info("...%s", var)`.
- ❌ `logger.error(str(e))` em vez de `logger.exception(...)`.
- ❌ `except: logger.error("erro"); pass` — engole exceção e perde contexto.
- ❌ Logar em arquivo dentro do container — quebra orquestração.
- ❌ Logger configurado em múltiplos lugares.
- ❌ Logar dados sensíveis sem mascarar.
- ❌ `logger.info("entrou na função X")` — ruído sem valor; use spans/tracing se precisa observabilidade fina.
