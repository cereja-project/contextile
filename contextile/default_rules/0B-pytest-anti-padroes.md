---
apply: by model decision
instructions: Apply when reviewing pytest-specific code for anti-patterns, or generating pytest tests to ensure these patterns never appear.
---

# Pytest — Anti-padrões Específicos

> **Aplica-se quando**: revisando código pytest, ou ao gerar testes pytest para garantir que esses padrões nunca apareçam.
>
> **Complementa**: `05-test-anti-padroes.md` (anti-padrões agnósticos de framework como `if`/`for` no corpo, dependência de ordem, sleep).

Anti-padrões específicos do **pytest** (sintaxe, ferramentas, configuração):

## Estilo xUnit em código novo

- ❌ Herdar de `unittest.TestCase`. Use funções `test_*` ou classes simples `Test*`.
- ❌ `setUp` / `tearDown`. Use fixtures com `yield`.
- ❌ `self.assertEqual(...)`, `self.assertTrue(...)`, `self.assertIsNone(...)`, etc. Use `assert` nativo.
- ❌ `self.assertRaises(X)`. Use `with pytest.raises(X, match=...)`.

```python
# ❌ estilo legado
class TestPedido(unittest.TestCase):
    def setUp(self):
        self.cliente = Cliente(...)

    def test_vip(self):
        self.assertEqual(self.cliente.tipo, "vip")
        with self.assertRaises(ValueError):
            self.cliente.aplicar_desconto(-10)

# ✅ pytest idiomático
@pytest.fixture
def cliente() -> Cliente:
    return Cliente(...)

def test_vip(cliente):
    assert cliente.tipo == "vip"

def test_desconto_negativo_invalido(cliente):
    with pytest.raises(ValueError, match="desconto inválido"):
        cliente.aplicar_desconto(-10)
```

## Fixtures

- ❌ Fixture com escopo `session`/`module` para objeto mutável compartilhado entre testes (vaza estado).
- ❌ Fixture chamando `mocker.patch` direto e retornando `None` — não dá pra customizar no teste, esconde o mock.
- ❌ Fixture com lógica de teste (asserções, Act) embutida.
- ❌ Cadeia de 5+ fixtures dependentes para um teste simples — refatore.
- ❌ Fixture com `params=[...]` sem `ids=[...]` — falhas viram lixo no relatório.
- ❌ Fixture nomeada genericamente (`data`, `obj`, `user`) — use nome que descreva o cenário (`usuario_admin_logado`, `pedido_com_3_itens`).
- ❌ Esquecer `pytest_asyncio.fixture` em fixture async sem `asyncio_mode = "auto"`.

## Parametrize

- ❌ `@pytest.mark.parametrize` sem `ids=` — falhas mostram tuplas opacas.
- ❌ Empilhar 3+ decoradores `parametrize` na mesma função — explosão combinatorial.
- ❌ Lógica condicional **dentro** do teste parametrizado (`if entrada > 0: assert ...`). Separe em testes.
- ❌ Misturar happy path e caso de erro no mesmo `parametrize` — erro precisa de `pytest.raises`, AAA diferente.
- ❌ Tuplas longas e opacas como parâmetros. Use `pytest.param(...)` com `id=`.

## Mocks (pytest-mock)

- ❌ `@patch(...)` ou `with patch(...)` quando `mocker` resolve mais limpo.
- ❌ `mocker.MagicMock()` sem `spec=` para mockar classe específica — perde detecção de mudanças de interface.
- ❌ Patch no path de **definição** em vez de **uso** (`requests.post` em vez de `meu_app.modulo.requests.post`).
- ❌ Mock async sem `AsyncMock` (ou sem `assert_awaited_*`).
- ❌ `mocker.patch("datetime.datetime.now")` — quebra outras chamadas. Use `freezegun` ou injeção de relógio.
- ❌ `assert mock.called` em vez de `mock.assert_called_once_with(...)` — perde argumentos.
- ❌ Múltiplos `mocker.patch` em um teste mockando coisas não relacionadas — teste está verificando demais.

## Asserções

- ❌ `try/except` para verificar exceção em vez de `pytest.raises`.
- ❌ `pytest.raises(Exception)` ou `pytest.raises(ValueError)` sem `match=`.
- ❌ Comparar floats com `==` em vez de `pytest.approx`.
- ❌ Código depois do `raise` esperado dentro do `with pytest.raises(...)` — nunca executa.
- ❌ Mensagem customizada redundante (`assert x == 5, "x deveria ser 5"`).
- ❌ Asserções **fora** do `with pytest.raises` que dependem do `raise` ter ocorrido sem capturar `exc_info`.

## Configuração e organização

- ❌ Markers não registrados em `pyproject.toml` (`@pytest.mark.foo` com typo passa silenciosamente sem `--strict-markers`).
- ❌ Sem `--strict-markers` e `--strict-config` em `addopts`.
- ❌ `pytest.ini` separado quando `pyproject.toml` resolve.
- ❌ Mudar `python_files` / `python_classes` / `python_functions` por preferência.
- ❌ `asyncio_mode = "strict"` em projeto async novo — força `@pytest.mark.asyncio` em todo teste.
- ❌ `pythonpath` ausente em projeto com layout `src/` — imports quebram.

## Output e execução

- ❌ `pytest -s` em CI — vaza dados sensíveis nos logs.
- ❌ `print()` deixado em teste como debug — vai pra captura e suja CI quando alguém usar `-s`.
- ❌ Testes pulados (`@pytest.mark.skip`) sem motivo documentado e prazo.
- ❌ `@pytest.mark.xfail(reason="bug 1234")` sem link/contexto suficiente — vira lixo permanente.
- ❌ Não usar `pytest-randomly` em projeto sério — dependências de ordem passam despercebidas.

## Conftest

- ❌ Lógica de produção em `conftest.py` (helpers que deveriam estar em `tests/fixtures/`).
- ❌ Fixtures duplicadas em vários `conftest.py` — mova para o ancestral comum.
- ❌ `conftest.py` na raiz do projeto (fora de `tests/`) — vira pollution global.
- ❌ Import de fixture de outro `conftest.py` direto — não é necessário, herança por pasta resolve.

## Async

- ❌ `async def` em teste sem `pytest-asyncio` instalado/configurado — teste passa sem rodar.
- ❌ Esquecer `await` em chamada async no teste — coroutine não executa, asserções não acontecem.
- ❌ Misturar testes sync e async no mesmo módulo sem clareza — confuso para mantenedores.
