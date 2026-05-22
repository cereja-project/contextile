---
apply: by model decision
instructions: Apply when using pytest.mark.parametrize, parametrizing fixtures, or handling multiple input cases in pytest.
---

# Pytest — Parametrização

> **Aplica-se quando**: testando a mesma lógica com múltiplas entradas no pytest, ou quando o corpo do teste contém `for`/`if` para iterar casos.
>
> **Complementa**: `01-test-estrutura.md` (princípio: sem `for`/`if` no corpo do teste).

## Regra fundamental

Sempre que testar a **mesma lógica com entradas diferentes**, use `@pytest.mark.parametrize`. **Nunca** use `for` no corpo do teste para iterar casos.

## Sempre forneça `ids=`

Sem `ids=`, o relatório do pytest mostra os valores brutos (ilegíveis pra tuplas complexas). Com `ids=`, cada caso vira uma falha nomeada e clara.

```python
@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("", False),
        ("a@b.com", True),
        ("invalido", False),
        ("a@b", False),
    ],
    ids=["vazio", "email_valido", "sem_arroba", "sem_dominio"],
)
def test_validador_de_email(entrada, esperado):
    assert validar_email(entrada) is esperado
```

Saída de falha legível: `test_validador_de_email[sem_dominio]`.

## Quando NÃO parametrizar

- Cenários **diferem em mais que valores** — ex: um caso precisa de mock, outro não. Faça testes separados.
- Os casos representam **regras de negócio distintas** que merecem nome próprio. DAMP > DRY: dois testes nomeados são melhores que um parametrizado genérico.
- A lista de parâmetros fica ilegível (tuplas longas, muitos `None`). Sinal de que os cenários não compartilham a mesma estrutura.

Exemplo ruim:

```python
# ❌ tupla incompreensível
@pytest.mark.parametrize(
    "a,b,c,d,e,f",
    [
        (1, "x", None, True, None, 5),
        (2, "y", "z", False, "k", None),
    ],
)
def test_algo(a, b, c, d, e, f): ...
```

Vire dois testes nomeados.

## `pytest.param` para casos com metadados

Para anexar `id`, `marks` ou ambos a um caso específico:

```python
@pytest.mark.parametrize(
    "valor, esperado",
    [
        pytest.param(0, 0, id="zero"),
        pytest.param(1, 1, id="positivo"),
        pytest.param(-1, 1, id="negativo"),
        pytest.param(
            10**18, 10**18,
            id="muito_grande",
            marks=pytest.mark.slow,
        ),
    ],
)
def test_valor_absoluto(valor, esperado):
    assert abs(valor) == esperado
```

`marks=` permite marcar um único caso como `slow`, `xfail`, `skip` sem afetar os outros.

## Empilhando parâmetros (produto cartesiano)

Para todas as combinações, empilhe decoradores:

```python
@pytest.mark.parametrize("moeda", ["BRL", "USD"], ids=["brl", "usd"])
@pytest.mark.parametrize("tipo_cliente", ["vip", "comum"], ids=["vip", "comum"])
def test_calculo_de_taxa(moeda, tipo_cliente): ...
```

Roda 4 combinações: `[brl-vip]`, `[brl-comum]`, `[usd-vip]`, `[usd-comum]`.

Use com **moderação** — 4 combinações é confortável, 16 é confuso. Acima de ~8-10 casos, refatore.

## Parametrizando fixtures

Para variar uma **dependência** (banco, formato), parametrize a fixture, não o teste:

```python
@pytest.fixture(params=["sqlite", "postgres"], ids=["sqlite", "postgres"])
def db(request):
    if request.param == "sqlite":
        yield criar_sqlite_em_memoria()
    else:
        yield criar_postgres_de_teste()
```

Todos os testes que usam `db` rodam contra ambos automaticamente — sem precisar mudar cada teste.

## Casos esperados de falha: `xfail`

Para casos conhecidos como falhos (bug em aberto, limitação documentada):

```python
@pytest.mark.parametrize(
    "entrada",
    [
        "ana@exemplo.com",
        pytest.param("a@b.c", marks=pytest.mark.xfail(reason="bug #1234: TLD curto rejeitado")),
    ],
)
def test_validador_email_aceita(entrada):
    assert validar_email(entrada) is True
```

`xfail` documenta o problema sem quebrar o build, e avisa se o caso **passa** (o bug foi corrigido sem atualizar o teste).

## Parametrização sobre tipos de input

Útil para testar a mesma lógica contra tipos diferentes:

```python
@pytest.mark.parametrize(
    "valor",
    [
        pytest.param(10, id="int"),
        pytest.param(10.0, id="float"),
        pytest.param(Decimal("10"), id="decimal"),
    ],
)
def test_aceita_numero(valor):
    assert eh_numero_positivo(valor) is True
```

## Anti-padrões pytest-específicos

- ❌ `@pytest.mark.parametrize` sem `ids=` — relatório de falha ilegível.
- ❌ Empilhar 3+ decoradores `parametrize` — explosão combinatorial.
- ❌ Tuplas longas e opacas como parâmetros. Use dataclass/dict via `pytest.param`.
- ❌ Lógica condicional **dentro** do teste parametrizado (`if valor > 0: assert ...`). Quebre em testes distintos ou mude a estrutura dos parâmetros.
- ❌ Parametrizar happy path + erro juntos no mesmo teste. Erro tem AAA diferente (`pytest.raises`) — separe.
