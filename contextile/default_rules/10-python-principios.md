---
apply: by model decision
instructions: Apply when writing, reviewing, or making design decisions in any Python code in this project.
---

# Python — Princípios Fundamentais

> **Aplica-se quando**: escrevendo, revisando ou refatorando qualquer código Python 3.12+ neste projeto. É a base para todas as outras regras de Python.

## Princípios que decidem trade-offs

Quando duas alternativas funcionam, escolha pela ordem:

1. **Explícito > implícito.** Argumentos nomeados, tipos visíveis, dependências passadas. Evite mágica (metaclasses, monkey patching, descritores customizados) sem necessidade clara.
2. **Simples > complexo, mas nunca simplista.** Prefira a solução mais simples que resolva o problema completo. Não simplifique a ponto de esconder casos.
3. **Composição > herança.** Herança apenas para "é um" verdadeiro e estável. Para reuso de comportamento, componha (passe colaboradores, use Protocol).
4. **Imutabilidade por padrão.** Listas/dicts/objetos que não precisam mudar devem ser imutáveis. `frozen=True` em dataclasses de domínio, tuplas em vez de listas para constantes.
5. **Funções puras quando possível.** Função que só depende dos argumentos e retorna um valor é mais testável, paralelizável e óbvia. Side effects ficam nas bordas do sistema.
6. **Pequeno > grande.** Funções com uma responsabilidade. Módulos coesos. Se um arquivo passa de ~400 linhas, provavelmente são dois módulos.

## Consistência > otimização pontual

Uma decisão de design pior, aplicada uniformemente, é melhor que uma decisão ótima aplicada em apenas parte do código. Se o projeto já segue um padrão, mantenha — proponha mudança apenas no nível de projeto, não em PRs pontuais.

## YAGNI e KISS

- **YAGNI** — não adicione abstração, configuração ou hook "para o caso de precisar". Adicione quando precisar.
- **KISS** — uma função, um propósito, um nível de abstração. Misturar baixo nível (manipulação de bytes) com alto nível (regra de negócio) na mesma função é defeito.

## Zen of Python — os pontos que importam

Os princípios do `import this` que mais impactam decisões diárias:

- *Beautiful is better than ugly.*
- *Explicit is better than implicit.*
- *Simple is better than complex.*
- *Flat is better than nested.* — Evite `for` dentro de `if` dentro de `try` dentro de `for`. Extraia funções.
- *Errors should never pass silently. Unless explicitly silenced.* — Nunca engula exceção sem decidir conscientemente.
- *There should be one obvious way to do it.* — Quando o projeto já tem convenção, siga.
- *If the implementation is hard to explain, it's a bad idea.*

## Quando quebrar uma regra

Regras existem para o caso comum. Quando quebrar, **comente o porquê**:

```python
# Performance: list comprehension é 3x mais lenta neste caso (perfilado).
result = []
for item in huge_iterable:
    if item.matches:
        result.append(item.transform())
```

Sem comentário, o próximo leitor (incluindo você daqui a 6 meses) vai "consertar" o código quebrando a otimização.
