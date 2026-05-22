---
apply: by model decision
instructions: Apply when writing or refactoring an individual test function, choosing test names, or deciding what literal values to use in the test body.
---

# Testes — Estrutura e Nomenclatura

> **Aplica-se quando**: escrevendo ou refatorando uma função de teste individual; escolhendo nome ou estruturando o corpo.

## Estrutura AAA

- Separe **Arrange**, **Act** e **Assert** por **uma linha em branco**.
- **Nunca** use comentários `# Arrange / # Act / # Assert`. A separação por linha em branco já comunica.
- A fase **Act é uma única chamada** — a operação sob teste.
- **Nunca** itere casos com `for` no corpo do teste. Use a parametrização do framework.
- Em testes triviais de uma linha (`assert soma(2, 2) == 4`), AAA pode ser implícito.

### ✅ Correto

```python
def test_calcular_desconto_aplica_10_porcento_para_cliente_vip():
    cliente = Cliente(tipo="vip")
    pedido = Pedido(valor=Decimal("100.00"), cliente=cliente)

    valor_final = pedido.aplicar_desconto()

    assert valor_final == Decimal("90.00")
```

### ❌ Errado (loop, branch, sem separação)

```python
def test_pedido():
    for tipo in ["vip", "comum"]:
        cliente = Cliente(tipo=tipo)
        pedido = Pedido(valor=100, cliente=cliente)
        if tipo == "vip":
            assert pedido.aplicar_desconto() == 90
        else:
            assert pedido.aplicar_desconto() == 100
```

## Nome do teste (DAMP)

Use **um** dos padrões abaixo e mantenha consistência no projeto:

- `test_<unidade>_<cenario>_<resultado_esperado>`
- `test_should_<resultado>_when_<cenario>`

### ✅ Bons nomes

```python
def test_login_com_senha_invalida_retorna_401(): ...
def test_should_raise_value_error_when_email_is_empty(): ...
def test_carrinho_vazio_nao_permite_checkout(): ...
```

### ❌ Nomes ruins

```python
def test_login(): ...               # vago
def test_1(): ...                   # sem significado
def test_user_creation_works(): ... # "works" não diz nada
def test_fix_bug_123(): ...         # descreve o histórico, não o comportamento
```

## Valores no corpo do teste (DAMP)

Prefira valores **literais e expressivos** dentro do teste — mesmo que repetidos — em vez de constantes globais opacas.

### ✅ DAMP — o cenário é óbvio lendo o teste

```python
def test_usuario_maior_de_idade_pode_se_cadastrar():
    usuario = Usuario(nome="Ana", idade=18)
    assert usuario.pode_cadastrar() is True
```

### ❌ DRY exagerado — esconde o cenário

```python
def test_usuario_maior_de_idade_pode_se_cadastrar():
    usuario = Usuario(nome=NOME_PADRAO, idade=IDADE_VALIDA)
    assert usuario.pode_cadastrar() is True
```

Constantes só fazem sentido quando o **valor exato é irrelevante** ao cenário (ex: `TOKEN_VALIDO = "tok_..."` em um teste cujo foco é o caminho de sucesso, não a validação do token).

## Use factory + override para valores não importantes

Quando o teste precisa de um objeto com 10 campos mas só 2 importam, use factory com override:

```python
def test_pedido_acima_de_500_aplica_frete_gratis():
    pedido = pedido_factory(valor=Decimal("600.00"))  # outros campos com defaults

    frete = calcular_frete(pedido)

    assert frete == Decimal("0.00")
```

A factory cobre o ruído (DRY); o teste destaca o que importa (DAMP).
