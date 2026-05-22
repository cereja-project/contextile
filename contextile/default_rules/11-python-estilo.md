---
apply: by model decision
instructions: Apply when formatting code, choosing names for variables/functions/classes, writing docstrings, or configuring ruff.
---

# Python — Estilo, Nomenclatura e Docstrings

> **Aplica-se quando**: escrevendo código Python e fazendo escolhas de formatação, nomes de variáveis/funções/classes, ou docstrings.

## Tooling

Use **ruff** como ferramenta única para lint e format. Não use `black`, `isort`, `flake8`, `pylint` em paralelo — ruff substitui todos.

Configuração mínima em `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "SIM", "RUF"]
ignore = []

[tool.ruff.format]
quote-style = "double"
```

`line-length = 100` é o equilíbrio moderno (PEP 8 sugere 79, mas 100 é o padrão de fato em projetos atuais).

## Nomenclatura

| Tipo                          | Convenção        | Exemplo                              |
| ----------------------------- | ---------------- | ------------------------------------ |
| Módulos e pacotes             | `snake_case`     | `pagamento_gateway.py`               |
| Funções e variáveis           | `snake_case`     | `calcular_desconto`, `total_pedido`  |
| Classes                       | `PascalCase`     | `PedidoRepository`, `ClienteVip`     |
| Constantes                    | `UPPER_SNAKE`    | `TIMEOUT_PADRAO`, `MAX_TENTATIVAS`   |
| "Privado" (convenção)         | `_leading`       | `_calcular_taxa_interna`             |
| Name mangling (raro)          | `__double_lead`  | use só para evitar conflito em herança |
| Type variables (PEP 695)      | `PascalCase`     | `def primeiro[T](items: list[T])`    |

### Nomes que comunicam

- Use **substantivos** para variáveis/atributos (`pedido`, `valor_total`).
- Use **verbos** para funções (`calcular_total`, `enviar_email`).
- Booleanos começam com `is_`, `has_`, `can_`, `should_` (`is_valid`, `has_estoque`).
- **Evite abreviações** exceto as universais (`db`, `url`, `id`, `i/j/k` em loops curtos).
- **Não codifique tipo no nome** (`lista_clientes` ❌, `clientes` ✅) — o type hint mostra.
- Evite negações: `is_invalid` é confuso com `not is_valid`. Prefira o nome positivo.

## Strings

- **f-strings** sempre para interpolação:
  ```python
  mensagem = f"Cliente {cliente.nome} tem {len(pedidos)} pedidos"
  ```
- Aspas duplas por padrão (ruff format aplica). Aspas simples só quando a string contém aspas duplas.
- f-string debug (3.8+) para logs/debug: `f"{valor=}"` imprime `valor=<repr>`.
- Strings multilinha longas: use parênteses + adjacência, não `\`:
  ```python
  msg = (
      "Linha um da mensagem "
      "linha dois sem quebra de linha real."
  )
  ```

## Paths

Use **`pathlib.Path`**, nunca `os.path` + strings:

```python
from pathlib import Path

config = Path("config") / "settings.toml"
if config.exists():
    texto = config.read_text(encoding="utf-8")
```

## Docstrings

Use **Google style** (parseável por mkdocs, Sphinx napoleon, e por LLMs).

```python
def calcular_desconto(pedido: Pedido, cupom: str | None = None) -> Decimal:
    """Calcula o desconto aplicável a um pedido.

    Considera o tipo do cliente (vip recebe 10%) e cupom opcional.
    Cupons inválidos são silenciosamente ignorados — não levantam erro.

    Args:
        pedido: Pedido com cliente e itens.
        cupom: Código do cupom promocional, se houver.

    Returns:
        Valor do desconto em reais, sempre >= 0.

    Raises:
        PedidoInvalidoError: Se o pedido não tiver itens.
    """
```

### Quando docstring é obrigatória

- **Sempre** em funções, métodos e classes públicas (sem `_` prefixo).
- **Sempre** em módulos públicos (no topo do arquivo).
- **Sempre** em serviços, repositórios, coletores, parsers e scripts ETL novos ou refatorados, mesmo quando o nome parece claro.
- **Opcional** em funções privadas curtas e óbvias.
- **Nunca** repita o que o nome e tipos já dizem:
  ```python
  # ❌ ruído
  def somar(a: int, b: int) -> int:
      """Soma dois inteiros."""
      return a + b
  ```

### Conteúdo da docstring

- Primeira linha: descreve **o que** faz, no imperativo, em uma frase.
- Linha em branco, depois detalhes (comportamentos não óbvios, edge cases, exemplos).
- Documente **comportamento**, não implementação ("aplica 10% para VIP" e não "usa if/else para verificar").
- Em código de domínio/ETL, documente o **contrato operacional**: origem dos dados, formato esperado, efeitos colaterais no banco, idempotência, regras de soft delete e chaves de conflito.
- Em refatorações, documente o **ponto central da regra** quando o objetivo for DRY. Ex.: se uma regra de status, upsert ou classificação foi extraída, a docstring deve indicar que aquele é o lugar canônico.

## Comentários

- Comentários explicam **por quê**, não **o quê**. O código já diz o quê.
- Use comentários curtos antes de blocos onde a intenção de negócio não aparece no código: compatibilidade entre dialetos, defesa contra dados inconsistentes de API, preservação de contrato legado, ou proteção por `settings.STOP_SYNC`.
- Prefira docstring para contrato público e comentário inline apenas para decisão local.
- `# TODO:`, `# FIXME:`, `# HACK:` devem incluir contexto e/ou referência a issue.
- Comentários desatualizados são pior que ausentes — sempre revise comentários ao mexer no código.
