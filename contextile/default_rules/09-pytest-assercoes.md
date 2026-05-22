---
apply: by model decision
instructions: Apply when using pytest-specific assertion tools (pytest.raises, pytest.approx, pytest.warns) or writing assertions in pytest tests.
---

# Pytest — Ferramentas de Asserção

> **Aplica-se quando**: usando ferramentas específicas do pytest para asserções (`pytest.raises`, `pytest.approx`, `pytest.warns`) ou decidindo a sintaxe correta.
>
> **Complementa**: `03-test-assercoes.md` (princípios: uma asserção lógica, específica vs genérica).

## `assert` nativo — sempre

Use o `assert` do Python — pytest faz **introspecção automática** e mostra os valores envolvidos na falha. **Nunca** use estilo xUnit em código novo.

```python
# ✅ pytest mostra "AssertionError: assert 5 == 6"
assert resultado == esperado

# ❌ estilo xUnit (unittest.TestCase)
self.assertEqual(resultado, esperado)
```

A introspecção do pytest mostra automaticamente:

- Valores comparados em ambos os lados.
- Diff em listas, dicts e objetos.
- Atributos relevantes.

Mensagens customizadas redundantes só ofuscam:

```python
# ❌ pytest já mostra os valores
assert x == 5, "x deveria ser 5"

# ✅ valor adicional ajuda diagnosticar
assert resp.status_code == 200, f"esperado 200, recebido {resp.status_code}: {resp.text}"
```

## `pytest.raises` — exceções esperadas

Use como context manager. **Sempre** verifique a mensagem com `match=` quando o tipo da exceção não for único:

```python
import pytest

def test_saque_acima_do_saldo_levanta_erro():
    conta = Conta(saldo=100)

    with pytest.raises(SaldoInsuficienteError, match="saldo insuficiente"):
        conta.sacar(150)
```

- `match=` aceita **regex**. Use texto literal simples quando bastar (`match="not found"`).
- Para verificar atributos da exceção, capture com `as`:

```python
def test_erro_inclui_id():
    with pytest.raises(PedidoNaoEncontrado) as exc_info:
        servico.buscar(42)

    assert exc_info.value.pedido_id == 42
```

`exc_info.value` é a exceção; `exc_info.type` é a classe; `exc_info.traceback` é o traceback.

### Errado: `try/except` em vez de `pytest.raises`

```python
# ❌ feio, fácil de quebrar (e se a exceção não acontecer?)
def test_saque_invalido():
    conta = Conta(saldo=100)
    try:
        conta.sacar(150)
        assert False, "deveria ter levantado erro"
    except SaldoInsuficienteError:
        pass
```

Use sempre `pytest.raises`.

## Múltiplas asserções fora do `with`

Não coloque mais código depois do `raise` esperado dentro do `with` — fica ambíguo:

```python
# ❌ ambíguo
with pytest.raises(SaldoInsuficienteError):
    conta.sacar(150)
    assert conta.saldo == 100  # nunca executa após o raise

# ✅ verificar estado APÓS o erro fora do with
with pytest.raises(SaldoInsuficienteError):
    conta.sacar(150)

assert conta.saldo == 100  # claro: estado deve ter sido preservado
```

## `pytest.approx` — comparação de floats

**Nunca** compare floats com `==` direto:

```python
# ❌ pode falhar com 0.30000000000000004
assert resultado == 0.1 + 0.2

# ✅ tolerância padrão (relativa, ~1e-6)
assert resultado == pytest.approx(0.3)
```

Configurações:

```python
# tolerância absoluta
assert resultado == pytest.approx(0.3, abs=1e-4)

# tolerância relativa explícita
assert resultado == pytest.approx(esperado, rel=1e-3)

# listas de floats
assert [r1, r2, r3] == pytest.approx([0.1, 0.2, 0.3])
```

Para valores monetários, **use `Decimal` em todo o caminho** — sem float, sem `approx`.

## `pytest.warns` — warnings esperados

Para validar emissão de warnings:

```python
def test_funcao_deprecated_avisa():
    with pytest.warns(DeprecationWarning, match="use nova_api"):
        funcao_legada()
```

Mesma estrutura de `pytest.raises`. Útil para validar `DeprecationWarning`, `UserWarning`, etc.

Para verificar **ausência** de warning, use `warnings.catch_warnings` direto — `pytest.warns` espera que pelo menos um warning ocorra.

## Asserções customizadas — quando criar

Em projetos grandes, pode valer criar helpers para asserções complexas e repetidas:

```python
# tests/fixtures/asserts.py
def assert_response_ok(resposta, esperado_id: int) -> None:
    assert resposta.status_code == 200
    assert resposta.json()["id"] == esperado_id
    assert "criado_em" in resposta.json()
```

Regras para helpers de asserção:

- Nome começa com `assert_*`.
- **Recebe** o objeto a verificar e os esperados.
- **Não** decide o cenário do teste — só verifica.
- Cada helper foca em **um conceito** verificado.

Se o helper tem mais de 4-5 asserções, provavelmente está verificando coisas demais. Quebre.

## Asserções sobre `dict` e estruturas aninhadas

```python
# ✅ comparação direta — pytest mostra diff
assert resposta.json() == {
    "id": 1,
    "nome": "Ana",
    "endereco": {"cidade": "Maceió", "uf": "AL"},
}

# Para subset (alguns campos), use comparação parcial
resposta_dict = resposta.json()
assert resposta_dict["nome"] == "Ana"
assert resposta_dict["endereco"]["cidade"] == "Maceió"
```

Para subset complexo, considere `dirty-equals` (lib opcional) ou crie helper.

## Asserções sobre coleções

```python
# Conteúdo exato com ordem
assert ids == [1, 2, 3]

# Conteúdo independente de ordem
assert sorted(ids) == [1, 2, 3]
# ou
assert set(ids) == {1, 2, 3}

# Tamanho específico
assert len(itens) == 5

# Verificar elemento presente com atributos
assert any(p.id == 42 and p.status == "ativo" for p in pedidos)
```

## Anti-padrões pytest-asserção-específicos

- ❌ `self.assertEqual`, `self.assertTrue`, `self.assertRaises` — estilo `unittest.TestCase`. Use `assert` + `pytest.raises`.
- ❌ `try/except` para verificar exceção em vez de `pytest.raises`.
- ❌ `assert resultado == valor` com floats sem `pytest.approx`.
- ❌ `pytest.raises` sem `match=` quando o tipo da exceção é genérico (`ValueError`, `RuntimeError`).
- ❌ Mensagem customizada redundante (`assert x == 5, "x deveria ser 5"`).
- ❌ Múltiplos comportamentos do código sob teste dentro do `with pytest.raises` — só a chamada que levanta o erro vai lá.
- ❌ Helpers de asserção que decidem o cenário do teste (misturam Arrange + Act + Assert).
