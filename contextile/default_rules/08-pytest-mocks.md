---
apply: by model decision
instructions: Apply when implementing mocks, patches, or time freezing in pytest tests, using pytest-mock or freezegun.
---

# Pytest — Mocks (pytest-mock, freezegun)

> **Aplica-se quando**: implementando mocks, patches ou freezing de tempo em testes pytest.
>
> **Complementa**: `02-test-isolamento.md` (conceito: onde mockar, o que NÃO mockar, injeção de relógio).

## Ferramenta: `pytest-mock`

Use a fixture `mocker` (pacote `pytest-mock`) em vez de empilhar `@patch` ou usar `with patch(...)`. Mais legível, sem ordem inversa de argumentos.

```python
def test_envia_email_de_boas_vindas(mocker):
    mock_smtp = mocker.patch("meu_app.email.smtplib.SMTP")
    usuario = Usuario(email="ana@exemplo.com")

    enviar_boas_vindas(usuario)

    mock_smtp.return_value.send_message.assert_called_once()
```

`mocker` cleanup automático ao fim do teste — não precisa de `try/finally`, `with`, ou `stopall`.

## Métodos principais de `mocker`

| Método                        | Uso                                                        |
| ----------------------------- | ---------------------------------------------------------- |
| `mocker.patch("path.to.X")`   | Patch de função/classe pelo path string                    |
| `mocker.patch.object(obj, "metodo")` | Patch de método em objeto/classe                   |
| `mocker.MagicMock()`          | Cria mock standalone (para injetar)                        |
| `mocker.Mock(spec=Classe)`    | Mock que respeita a interface da classe (recomendado)      |
| `mocker.AsyncMock()`          | Mock de coroutine async                                    |
| `mocker.spy(obj, "metodo")`   | Wrapper que registra chamadas mas executa o real           |

## Patch no local certo

A regra clássica: **patch onde é usado, não onde é definido**.

```python
# meu_app/notif.py
import requests

def enviar(url, dados):
    return requests.post(url, json=dados)

# tests/test_notif.py
def test_enviar(mocker):
    # ❌ não funciona — patch no módulo errado
    mocker.patch("requests.post")

    # ✅ patch no local onde foi importado
    mocker.patch("meu_app.notif.requests.post")

    from meu_app.notif import enviar
    enviar("http://x", {"a": 1})
```

## `spec` — mock que respeita a interface

```python
# ❌ mock genérico — aceita qualquer método, esconde mudanças de interface
gateway = mocker.MagicMock()
gateway.metodo_inexistente()  # passa sem erro

# ✅ mock com spec — só permite métodos que existem na classe real
gateway = mocker.Mock(spec=PagamentoGateway)
gateway.metodo_inexistente()  # AttributeError: spec não tem esse método
```

Sempre prefira `spec=` quando estiver mockando uma classe específica. Pega bugs cedo (refatorou nome do método e esqueceu de atualizar o teste).

## Verificação de chamadas

```python
# verificar UMA chamada exata
mock.assert_called_once_with(arg=valor, outro=10)

# verificar nunca chamado
mock.assert_not_called()

# verificar chamada SEM checar argumentos
mock.assert_called()

# verificar múltiplas chamadas em ordem
mock.assert_has_calls([
    call(1),
    call(2),
    call(3),
])

# acessar argumentos da última chamada
args, kwargs = mock.call_args
```

Prefira **`assert_called_once_with`** — verifica contagem **e** argumentos juntos. Use só `assert_called()` quando os argumentos genuinamente não importam.

## Mocks async

Para coroutines, use `AsyncMock`:

```python
async def test_busca_externa(mocker):
    mock_client = mocker.AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = httpx.Response(200, json={"ok": True})

    resultado = await buscar_dados(mock_client, "/path")

    assert resultado == {"ok": True}
    mock_client.get.assert_awaited_once_with("/path")
```

Notas:

- Em código async, use `assert_awaited_once_with(...)` em vez de `assert_called_once_with(...)` — verifica que `await` foi feito.
- `mocker.patch` retorna `AsyncMock` automaticamente quando o alvo é uma função async (Python 3.8+).

## Patching de classes inteiras

```python
def test_usa_repositorio(mocker):
    # patch da classe inteira
    mock_repo_class = mocker.patch("meu_app.servico.PedidoRepository")

    # instâncias criadas dentro do código sob teste retornam o mesmo mock
    mock_repo = mock_repo_class.return_value
    mock_repo.buscar.return_value = pedido_teste

    servico = PedidoServico()  # internamente faz PedidoRepository(session)
    resultado = servico.consultar(1)

    assert resultado == pedido_teste
```

Prefira **injeção de dependência** sempre que possível — mockar classe direto é cheiro de design acoplado.

## Tempo: `freezegun` com pytest

Quando injeção de relógio não é prática:

```python
from freezegun import freeze_time

@freeze_time("2026-05-21 10:00:00")
def test_relatorio_marca_data_atual():
    relatorio = gerar_relatorio()
    assert relatorio.gerado_em == datetime(2026, 5, 21, 10, 0, 0, tzinfo=UTC)
```

Como context manager:

```python
def test_expira_apos_5_minutos():
    with freeze_time("2026-05-21 10:00:00") as frozen:
        token = criar_token()

        frozen.tick(timedelta(minutes=5, seconds=1))

        assert token.expirado() is True
```

**Sempre** prefira injeção de relógio (ver `02-test-isolamento.md`). `freezegun` fica para código legado ou libs externas que não dá pra injetar.

## Randomização

Não mocke `random` direto. Injete uma seed (princípio em `02-test-isolamento.md`). Quando não dá:

```python
def test_embaralha(mocker):
    mocker.patch("meu_app.utils.random.shuffle", side_effect=lambda x: x)
    # x permanece na mesma ordem
```

## Override de fixtures de dependência (FastAPI)

Para apps FastAPI, `dependency_overrides` (ver `22-fastapi-dependencias.md`) é mais limpo que `mocker.patch`:

```python
# em conftest.py
@pytest.fixture
def app_test():
    app.dependency_overrides[get_current_user] = lambda: usuario_teste
    yield app
    app.dependency_overrides.clear()
```

Use `mocker.patch` para código que **não** passa por DI.

## Anti-padrões pytest-mock-específicos

- ❌ `with patch(...)` ou `@patch(...)` quando `mocker` faz a mesma coisa mais limpo.
- ❌ `Mock()` sem `spec=` para mockar uma classe — perde checagem de interface.
- ❌ Patch no path da definição em vez do uso (`requests.post` em vez de `meu_app.modulo.requests.post`).
- ❌ Esquecer `assert_awaited_*` em mocks async.
- ❌ `mocker.patch("datetime.datetime.now")` — quebra outras chamadas internas. Use `freezegun` ou injeção.
- ❌ `mock.call_count == 1` quando `assert_called_once_with(...)` é mais expressivo.
- ❌ Vários `mocker.patch` no mesmo teste mockando coisas não relacionadas — sinal de teste verificando demais.
