---
apply: by model decision
instructions: Apply when reviewing Python code for anti-patterns and code smells, or generating Python code to ensure these patterns never appear.
---

# Python — Anti-padrões Proibidos

> **Aplica-se quando**: revisando código Python, identificando code smells, ou gerando código para garantir que esses padrões nunca apareçam.

Ao gerar ou aceitar código, **nunca** produza nem aprove:

## Estrutura e fluxo

- ❌ `from X import *` — polui namespace, esconde origem.
- ❌ `except:` ou `except Exception:` sem motivo documentado fora da borda do sistema.
- ❌ `except: pass` ou `except Exception: pass` sem comentário explicando.
- ❌ Engolir exceção sem logar nem reerguer.
- ❌ Usar exceção para fluxo de controle normal (sair de loop, "não encontrado").
- ❌ Try-block gigante cobrindo várias operações independentes.
- ❌ Re-raise sem `from e` perdendo o traceback original.

## Argumentos e retornos

- ❌ Mutable default args (`def f(x: list = [])`). Use `None` + check.
- ❌ Mais de ~5 parâmetros em uma função. Agrupe em dataclass/Pydantic.
- ❌ Argumentos booleanos posicionais (`func(True, False, True)`). Use `*` + keyword-only.
- ❌ Retornar tipos inconsistentes da mesma função (`Cliente | None | list[Cliente]`).
- ❌ Retornar tupla anônima com mais de 2 elementos. Use `NamedTuple` ou `dataclass`.

## Estado e mutação

- ❌ Variáveis globais mutáveis.
- ❌ Singleton "manual" (`_INSTANCIA = None` + função `get_instance`). Use injeção de dependência.
- ❌ Mutar argumento de entrada sem deixar explícito no nome/docstring.
- ❌ Atributos de classe mutáveis compartilhados entre instâncias:
  ```python
  class X:
      itens = []  # ❌ compartilhado entre todas as instâncias
  ```

## Tipos

- ❌ `Any` fora de boundary com biblioteca sem tipos.
- ❌ `Optional[X]` em código Python 3.10+. Use `X | None`.
- ❌ `List[X]`, `Dict[K, V]` em código Python 3.9+. Use `list[X]`, `dict[K, V]`.
- ❌ `Union[X, Y]`. Use `X | Y`.
- ❌ `# type: ignore` sem código específico (`# type: ignore[arg-type]`).
- ❌ `cast()` sem comentário justificando.

## Comparações e checagens

- ❌ `if x == None`, `if x == True`, `if x == False`. Use `is None`, `if x`, `if not x`.
- ❌ `type(x) == Y`. Use `isinstance(x, Y)`.
- ❌ `len(lista) == 0`. Use `not lista`.
- ❌ `if len(lista) > 0`. Use `if lista`.

## Strings

- ❌ `"texto" + variavel + "mais texto"`. Use f-string.
- ❌ `%` formatting (`"valor: %s" % x`). Use f-string.
- ❌ `.format()`. Use f-string. (Exceção: templates externos.)
- ❌ Concatenação de strings em loop com `+=`. Use `"".join(lista)`.

## Arquivos e paths

- ❌ `os.path.join`, `os.path.exists`, `os.path.dirname`. Use `pathlib.Path`.
- ❌ `open(arquivo)` sem `with`.
- ❌ Ler arquivo grande inteiro em memória com `.read()` se dá pra processar em stream.
- ❌ `open(arquivo)` sem `encoding="utf-8"` (no Windows default é cp1252).

## Logging e I/O

- ❌ `print()` em código de produção. Use `logger`.
- ❌ `logger.error(str(e))` capturando exceção. Use `logger.exception(...)` ou `exc_info=e`.
- ❌ `logger.info(f"valor: {valor}")` com f-string pré-formatada. Use `logger.info("valor: %s", valor)` — lazy evaluation, melhor performance e parser de logs estruturados pega os args.
- ❌ Strings de log sem contexto (`"erro"`, `"falha"`). Inclua o que falhou e identificadores.

## Classes

- ❌ Herança múltipla complexa (MRO confuso). Prefira composição ou um único pai + Protocol.
- ❌ Classes com apenas um método `execute()`/`run()`. É uma função disfarçada.
- ❌ `@property` que faz I/O ou cálculo caro. Use método (`obter_total()`).
- ❌ `@property` com side effect (set/cache/log). Surpreende o leitor.
- ❌ Métodos mágicos (`__add__`, `__call__`) sem semântica clara e idiomática.

## Segurança

- ❌ `eval()`, `exec()` sobre input externo.
- ❌ `pickle.load` de fonte não confiável.
- ❌ SQL por concatenação de string (`f"SELECT * FROM x WHERE id = {id}"`). Use parametrização.
- ❌ Secrets hardcoded (tokens, senhas, chaves API). Use env vars ou secret manager.
- ❌ `subprocess.run(comando, shell=True)` com input externo.

## Performance

- ❌ Lista quando set/dict resolve com lookup O(1):
  ```python
  # ❌ O(n) por iteração
  if item.id in [x.id for x in todos]: ...
  # ✅ O(1)
  ids = {x.id for x in todos}
  if item.id in ids: ...
  ```
- ❌ Construir lista intermediária quando generator basta:
  ```python
  # ❌ aloca lista inteira só pra somar
  total = sum([x.preco for x in itens])
  # ✅
  total = sum(x.preco for x in itens)
  ```
- ❌ Otimização sem perfilamento. Profile primeiro, otimize depois.

## Outros

- ❌ Comentários óbvios (`x = x + 1  # incrementa x`).
- ❌ Comentários desatualizados que contradizem o código.
- ❌ Código comentado deixado no repo. Use Git.
- ❌ `TODO` sem nome/data/issue. Vira lixo permanente.
- ❌ Magic numbers/strings (`if tipo == 3:`). Use enums ou constantes nomeadas.
- ❌ Funções/módulos com nomes genéricos (`utils.py`, `helpers.py`, `manager.py`). Nome o que ele faz.
- ❌ Arquivos com mais de ~400 linhas. Provavelmente são vários módulos.
