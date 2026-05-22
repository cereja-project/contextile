---
apply: by model decision
instructions: Apply when defining functions, methods, classes, dataclasses, or deciding between function and class.
---

# Python — Design de Funções e Classes

> **Aplica-se quando**: definindo funções, métodos ou classes; decidindo entre função e classe; modelando dados internos.

## Funções

### Tamanho e responsabilidade

- Uma função faz **uma coisa** e tem **um nível de abstração**.
- Se a função tem mais de ~30 linhas ou >2 níveis de indentação, **extraia funções auxiliares**.
- Não misture orquestração com cálculo: a função "fluxo de pagamento" chama `calcular_taxa`, `validar_cartao`, `cobrar` — não faz tudo inline.

### Pureza

Prefira **funções puras** (mesmas entradas → mesmas saídas, sem side effects). Empurre I/O e mutação para as bordas:

```python
# ✅ núcleo puro
def calcular_total(itens: Sequence[Item], cupom: Cupom | None) -> Decimal:
    subtotal = sum(item.preco for item in itens)
    desconto = cupom.aplicar(subtotal) if cupom else Decimal("0")
    return subtotal - desconto

# borda faz I/O
def processar_checkout(pedido_id: int, repo: PedidoRepo) -> None:
    pedido = repo.buscar(pedido_id)
    pedido.total = calcular_total(pedido.itens, pedido.cupom)
    repo.salvar(pedido)
```

### Argumentos

- **Argumentos posicionais**: para os 1-2 parâmetros essenciais e óbvios pela ordem.
- **Keyword-only** (após `*`): para opções, flags, configurações:
  ```python
  def conectar(host: str, port: int, *, timeout: float = 30, retries: int = 3) -> Conn: ...
  conectar("db.local", 5432, timeout=60)
  ```
- **Positional-only** (antes de `/`): raro, use para argumentos cujo nome não interessa ao caller:
  ```python
  def somar(a: int, b: int, /) -> int: ...
  ```
- **Máximo ~5 parâmetros**. Acima disso, agrupe em dataclass/Pydantic model.

### Mutable default args — NUNCA

```python
# ❌ bug clássico: a lista é compartilhada entre chamadas
def adicionar(item: str, lista: list[str] = []) -> list[str]:
    lista.append(item)
    return lista

# ✅
def adicionar(item: str, lista: list[str] | None = None) -> list[str]:
    if lista is None:
        lista = []
    lista.append(item)
    return lista
```

Vale para `[]`, `{}`, `set()`, instâncias de classe. Apenas valores imutáveis (`None`, `0`, `"texto"`, `True`, tuplas, `frozenset`) podem ser default direto.

### Retornos

- **Tipo de retorno consistente**. Não retorne `Cliente | None | list[Cliente]` na mesma função — divida.
- Evite múltiplos `return` com tipos diferentes mascarados por `Any`.
- Não retorne tupla sem tipos nomeados se passar de 2 elementos — use `NamedTuple` ou `dataclass`.

## Classes

### Quando usar classe

Use classe quando há **estado + comportamento que andam juntos** e fazem sentido como entidade. Exemplos legítimos: `Repository`, `Service`, `Cliente`, `Pedido`.

Não use classe para:

- Agrupar funções soltas sem estado (use módulo).
- Forçar OOP em scripts simples.
- Substituir um dicionário/dataclass (se só guarda dados, use `@dataclass`).

### `@dataclass` para dados

Para classes que carregam dados (DTOs, value objects, configs), use `@dataclass`. Defaults recomendados:

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True, kw_only=True)
class Cliente:
    id: int
    nome: str
    email: str
    tipo: TipoCliente = TipoCliente.COMUM
```

- `frozen=True` — imutável após criação. Mutação cria nova instância.
- `slots=True` — menos memória, evita atributos não declarados.
- `kw_only=True` — força keyword args na criação, evita erros de ordem.

Quebre defaults só quando há motivo concreto (ex: hashing custom, mutação intencional).

### Composição > herança

Prefira injetar colaboradores:

```python
# ✅ composição
class PedidoService:
    def __init__(self, repo: PedidoRepo, notif: Notificador):
        self._repo = repo
        self._notif = notif

    def finalizar(self, pedido_id: int) -> None:
        pedido = self._repo.buscar(pedido_id)
        pedido.finalizar()
        self._repo.salvar(pedido)
        self._notif.enviar(pedido.cliente.email, "Pedido confirmado")
```

Não:

```python
# ❌ herança como reuso de código
class PedidoService(NotificadorMixin, RepoMixin): ...
```

Herança fica para "**é um** verdadeiro" em hierarquias estáveis. Não para reuso de código.

### Métodos

- `self` para método de instância (operações sobre o objeto).
- `@classmethod` para construtores alternativos (`Cliente.from_dict(...)`).
- `@staticmethod` raramente — geralmente é função de módulo disfarçada.
- `@property` apenas para acesso barato e sem side effect. Operações que custam ou mutam devem ser métodos.

### Encapsulamento

Python não tem `private` real, mas siga a convenção:

- `_atributo` ou `_metodo` — privado por convenção, não acesse de fora.
- Não use `__atributo` (name mangling) exceto para evitar conflito em herança.
- API pública é o que **não** começa com `_`.

## Quando função, quando classe?

- **Função** quando: transformação stateless, utilitário, cálculo puro.
- **`@dataclass`** quando: estrutura de dados com pouca lógica.
- **Classe** quando: estado mutável compartilhado entre métodos, ciclo de vida (open/close), dependências injetadas.
- **Módulo** quando: agrupar funções relacionadas que não compartilham estado.

Se a "classe" tem apenas um método público chamado `execute()` ou `run()`, **provavelmente é uma função**.
