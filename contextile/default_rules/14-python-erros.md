---
apply: by model decision
instructions: Apply when handling exceptions, defining custom exception hierarchies, using context managers, or deciding between raise and return None.
---

# Python — Erros e Exceções

> **Aplica-se quando**: tratando exceções, definindo hierarquias customizadas, usando context managers, ou decidindo entre lançar erro, retornar `None`, ou logar.

## Exceções específicas

- **Nunca** capture `Exception` ou bare `except` exceto na borda do sistema (handler HTTP, main loop de worker, retry decorator).
- Capture o tipo mais específico possível:
  ```python
  # ✅
  try:
      cliente = repo.buscar(id)
  except ClienteNaoEncontrado:
      return None

  # ❌ engole erros não relacionados (DB down, bug, etc.)
  try:
      cliente = repo.buscar(id)
  except Exception:
      return None
  ```

## Hierarquia customizada por domínio

Crie uma exceção base do seu domínio e derive as específicas. Facilita captura ampla na borda e específica no núcleo:

```python
class AppError(Exception):
    """Base de todas as exceções da aplicação."""

class PedidoError(AppError):
    """Erros relacionados a pedidos."""

class PedidoNaoEncontrado(PedidoError):
    def __init__(self, pedido_id: int):
        self.pedido_id = pedido_id
        super().__init__(f"Pedido {pedido_id} não encontrado")

class PedidoJaFinalizado(PedidoError): ...
```

Inclua **dados estruturados** no `__init__` (ids, valores) para que handlers/logs possam usar — não apenas mensagem em string.

## `raise X from e` ao recapturar

Sempre encadeie a exceção original:

```python
try:
    response = httpx.get(url, timeout=5)
    response.raise_for_status()
except httpx.HTTPError as e:
    raise IntegracaoGatewayError(f"Falha ao chamar {url}") from e
```

Sem `from`, o traceback original some — debugging vira pesadelo.

## EAFP > LBYL

Pythônico é **Easier to Ask Forgiveness than Permission** — tente e capture, em vez de checar antes:

```python
# ✅ EAFP
try:
    valor = config["timeout"]
except KeyError:
    valor = TIMEOUT_PADRAO

# ❌ LBYL — race condition em código concorrente, mais verboso
if "timeout" in config:
    valor = config["timeout"]
else:
    valor = TIMEOUT_PADRAO

# ✅ ainda melhor para dicts
valor = config.get("timeout", TIMEOUT_PADRAO)
```

LBYL faz sentido quando a checagem é barata e o erro caro (validação de entrada antes de operação destrutiva).

## Não use exceção para fluxo normal

Exceção é para o que é **excepcional**. Sair de loop, indicar "não achei", retornar caminho alternativo — não são exceções.

```python
# ❌ exceção para controle de fluxo
def buscar_cliente(id: int) -> Cliente:
    cliente = repo.find(id)
    if not cliente:
        raise ClienteNaoEncontrado
    return cliente

resultado = None
try:
    resultado = buscar_cliente(id)
except ClienteNaoEncontrado:
    pass  # tratamento idêntico a "achou nada"

# ✅ retorne None ou Optional
def buscar_cliente(id: int) -> Cliente | None:
    return repo.find(id)
```

A regra: se "não achou" é um caso normal e esperado, retorne `None`. Se é violação de invariante (caller assumiu que existe), levante exceção.

## `try` cobre só o que pode falhar

```python
# ❌ try gigante esconde origem da falha
try:
    cliente = repo.buscar(id)
    pedidos = listar_pedidos(cliente)
    total = sum(p.valor for p in pedidos)
    return formatar_relatorio(cliente, pedidos, total)
except Exception as e:
    logger.error("erro", exc_info=e)
    return None

# ✅ try cobre só o I/O propenso a falha
cliente = repo.buscar(id)
if cliente is None:
    return None
try:
    pedidos = listar_pedidos(cliente)
except IntegracaoError as e:
    logger.exception("Falha ao listar pedidos de %s", cliente.id)
    raise
total = sum(p.valor for p in pedidos)
return formatar_relatorio(cliente, pedidos, total)
```

## Nunca engula exceções silenciosamente

```python
# ❌ silêncio é bug futuro
try:
    salvar(dados)
except Exception:
    pass

# ✅ se intencional, comente o porquê
try:
    cache.invalidar(chave)
except CacheIndisponivel:
    # Cache opcional — operação principal não pode falhar por isso.
    logger.warning("cache indisponível, prosseguindo sem invalidar")
```

`except: pass` ou `except Exception: pass` sem comentário é proibido.

## Logging de exceção

Use `logger.exception(...)` dentro de `except` — captura traceback automaticamente:

```python
try:
    processar()
except IntegracaoError:
    logger.exception("Falha em processar pedido %s", pedido_id)
    raise
```

Fora de `except`, use `exc_info=e`:

```python
logger.error("Falha", exc_info=e)
```

Nunca apenas `logger.error(str(e))` — perde o traceback.

## Context managers para recursos

Use `with` para qualquer recurso que precisa ser fechado/limpo:

```python
# ✅
with open(arquivo) as f:
    dados = f.read()

with conn.begin() as transaction:
    repo.salvar(pedido)
    repo.salvar(item)

# ❌
f = open(arquivo)
dados = f.read()
f.close()  # não roda se read() lançar
```

Para múltiplos recursos:

```python
with (
    open(entrada) as entrada_f,
    open(saida, "w") as saida_f,
):
    saida_f.write(entrada_f.read())
```

Crie context managers customizados com `@contextlib.contextmanager` quando precisar de setup/teardown reutilizável.

## Validação na borda

Valide entrada externa **na borda do sistema** (handler HTTP, parser de CSV, leitor de fila) — não em cada função interna. Núcleo trabalha com tipos já válidos.

```python
# borda
def criar_pedido_handler(payload: dict) -> Response:
    try:
        dados = PedidoCreate.model_validate(payload)  # Pydantic
    except ValidationError as e:
        return Response(422, e.errors())
    pedido = service.criar(dados)  # tipos garantidos daqui pra frente
    return Response(201, pedido)
```

Isso elimina checagens defensivas espalhadas pelo código.
