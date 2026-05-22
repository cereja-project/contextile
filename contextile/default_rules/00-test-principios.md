---
apply: by model decision
instructions: Apply when writing, reviewing, refactoring, or generating tests in any framework, or making decisions about how to structure test code.
---

# Testes — Princípios Fundamentais

> **Aplica-se quando**: escrevendo, revisando ou refatorando testes em qualquer framework (pytest, unittest, etc.). Base conceitual; especializações por framework ficam em arquivos próprios (ex: `06-pytest-fixtures.md`).

## Os três princípios

Toda decisão em código de teste equilibra:

- **AAA** (Arrange, Act, Assert) — toda função de teste tem essa estrutura.
- **DAMP** (Descriptive And Meaningful Phrases) — testes são documentação executável; legibilidade vence sobre desduplicação.
- **DRY** (Don't Repeat Yourself) — use apenas em encanamento (fixtures, factories, helpers de setup), nunca para esconder a intenção do teste.

**Regra de ouro:** DRY em código de produção, DAMP em código de teste.

## Tabela de decisão DAMP vs DRY

| Situação                                                    | Princípio dominante |
| ----------------------------------------------------------- | ------------------- |
| Criar objeto de domínio com defaults                        | DRY (factory)       |
| Login/autenticação que não é o foco do teste                | DRY (helper)        |
| Limpar banco antes de cada teste                            | DRY (fixture)       |
| Definir o cenário específico do teste                       | DAMP (no corpo)     |
| Nome do teste                                               | DAMP                |
| Asserção principal                                          | DAMP                |
| Mesma lógica com entradas diferentes                        | DRY (parametrização) |
| Testes parecidos que representam regras diferentes          | DAMP (separados)    |

## Onde DRY se aplica

Use abstrações reutilizáveis para **encanamento que não é o foco do teste**:

- **Fixtures** — objetos, conexões, dependências comuns.
- **Factories** — defaults sensatos + overrides explícitos para campos relevantes.
- **Helpers** — ações fora do foco (login, popular banco, etc.).
- **Setup/Teardown** — limpar banco, resetar cache, gerenciar containers.

## Onde DRY NÃO se aplica

- A abstração **esconde o que o teste verifica** — leitor precisa abrir outros arquivos para entender o cenário.
- Helper precisa de muitos parâmetros/flags para cobrir variações (`helper(login=True, criar_pedido=False, ...)`).
- Helper faz **mais de uma coisa** ou muda comportamento por flag.
- Helpers/fixtures que executam o **Act** do teste — Act sempre fica visível no corpo.
- A duplicação está nas **asserções principais** — repeti-las é a intenção do teste.

## Verificação rápida

Se ao ler **apenas o corpo do teste** o cenário não é compreensível, removeu informação demais. Reverta a abstração.

## Checklist genérico antes de propor um teste

- [ ] Nome descreve cenário + comportamento esperado.
- [ ] AAA visível por linhas em branco (sem comentários `# Arrange`/`# Act`/`# Assert`).
- [ ] Uma única ação na fase Act.
- [ ] Sem `if`/`for` no corpo (use parametrização do framework).
- [ ] Sem dependência de ordem de execução.
- [ ] Dependências externas mockadas nos limites.
- [ ] Asserções específicas, não genéricas.
- [ ] Helpers/fixtures cobrem ruído, não a lógica testada.
- [ ] Lendo só o teste, o cenário é compreensível.
