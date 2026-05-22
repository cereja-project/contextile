---
apply: by model decision
instructions: Apply when writing the Assert phase of a test, deciding what to verify, or composing assertion messages, regardless of framework.
---

# Testes — Princípios de Asserção

> **Aplica-se quando**: escrevendo a fase Assert de um teste; decidindo o que verificar e como. Sintaxe específica de framework (ex: `pytest.raises`, `pytest.approx`) fica em arquivos próprios.

## Uma asserção lógica por teste

- Múltiplas linhas `assert` são aceitáveis quando verificam **o mesmo conceito** (ex: vários campos de uma resposta HTTP).
- Múltiplas asserções verificando **comportamentos distintos** = vários testes.

### ✅ Várias asserções, mesmo conceito (resposta de criação)

```python
def test_criar_usuario_retorna_201_com_dados_completos():
    resposta = client.post("/usuarios", json={"nome": "Ana"})

    assert resposta.status_code == 201
    assert resposta.json()["nome"] == "Ana"
    assert "id" in resposta.json()
```

### ❌ Várias asserções, conceitos distintos (vire 3 testes)

```python
def test_servico_de_pedidos():
    pedido = criar_pedido(...)
    assert pedido.id is not None             # testa criação

    pedido.adicionar_item(...)
    assert len(pedido.itens) == 1            # testa adição de item

    pedido.finalizar()
    assert pedido.status == "finalizado"     # testa finalização
```

## Asserções específicas, não genéricas

| Genérica (evite)              | Específica (use)                       |
| ----------------------------- | -------------------------------------- |
| `assert resultado`            | `assert resultado == valor_esperado`   |
| `assert resultado is not None`| `assert isinstance(resultado, Pedido)` |
| `assert len(lista)`           | `assert len(lista) == 3`               |
| `assert "ok" in resposta`     | `assert resposta == {"status": "ok"}`  |
| `assert pedido.valido()`      | `assert pedido.valido() is True`       |

Asserções vagas escondem regressões. Se algo mudar de `5` para `7`, `assert resultado` continua passando e o bug passa despercebido.

## Teste comportamento, não implementação

Asserte o **resultado observável** (entrada → saída ou efeito), não detalhes de como foi feito.

```python
# ❌ testa implementação
def test_calcular_total_usa_for_em_itens(mocker):
    spy = mocker.spy(builtins, "sum")
    calcular_total([item_a, item_b])
    spy.assert_called_once()  # ninguém quer saber se usa sum() ou for

# ✅ testa comportamento
def test_calcular_total_soma_precos_dos_itens():
    total = calcular_total([Item(preco=10), Item(preco=20)])
    assert total == Decimal("30")
```

Testes acoplados à implementação quebram em refatorações que **não mudam comportamento** — sinal de teste ruim.

## Asserções compostas e estrutura completa

Quando faz sentido verificar a estrutura inteira do resultado, asserte contra ela:

```python
# ✅ asserção da estrutura toda
def test_buscar_cliente_retorna_dados_completos():
    cliente = servico.buscar(1)

    assert cliente == Cliente(
        id=1,
        nome="Ana Silva",
        email="ana@x.com",
        tipo=TipoCliente.VIP,
    )
```

Mais legível que 4 asserções separadas, e a falha mostra o diff completo.

## Asserções sobre coleções

```python
# Conteúdo exato
assert ids == [1, 2, 3]

# Conteúdo independente de ordem
assert set(ids) == {1, 2, 3}

# Subconjunto
assert {1, 2}.issubset(set(ids))

# Tamanho específico
assert len(itens) == 5

# Algum elemento atende condição
assert any(p.total > 1000 for p in pedidos)

# Todos atendem
assert all(p.status == "ativo" for p in pedidos)
```

Escolha a forma mais expressiva. `any`/`all` perdem informação na falha — `len() == N` ou comparação direta dá mensagem melhor.

## Exceções esperadas

Toda framework de teste tem uma forma idiomática de capturar exceções esperadas. **Sempre** verifique:

1. **O tipo** da exceção.
2. **A mensagem** (ou um padrão dela), quando o tipo não é único.

```python
# pseudo-código framework-agnóstico
with assert_raises(SaldoInsuficienteError, message_matches="saldo insuficiente"):
    conta.sacar(150)
```

Sem verificar mensagem, qualquer `SaldoInsuficienteError` (até de bug em código não relacionado) faz o teste passar.

Detalhes pytest: `09-pytest-assercoes.md`.

## Comparação de floats

**Nunca** compare floats com `==` direto — erros de ponto flutuante quebram testes em momentos aleatórios:

```python
# ❌
assert resultado == 0.1 + 0.2  # pode falhar: 0.30000000000000004 != 0.3

# ✅ use tolerância (framework-específico)
assert resultado == pytest.approx(0.3)
```

Para valores monetários, use `Decimal` em todo o caminho — sem float.

## Mensagens de asserção customizadas

Adicione mensagem **apenas** quando a falha não é autoexplicativa pelo `assert` do framework:

```python
# ✅ valor adicional ajuda diagnosticar
assert resposta.status_code == 200, (
    f"Esperado 200, recebido {resposta.status_code}: {resposta.text}"
)

# ❌ redundante - framework já mostra os valores
assert x == 5, "x deveria ser 5"
```

Frameworks modernos (pytest) fazem introspecção e mostram o diff automaticamente. Mensagem customizada só agrega quando inclui **contexto que não está visível** no assert (ex: corpo da resposta, query SQL, dump do estado).
