---
apply: by model decision
instructions: Apply when reviewing test code for anti-patterns and code smells, regardless of framework, or generating tests to ensure these never appear.
---

# Testes — Anti-padrões Gerais

> **Aplica-se quando**: revisando código de teste de qualquer framework, identificando code smells, ou ao gerar testes para garantir que esses padrões nunca apareçam. Anti-padrões específicos de pytest ficam em `0B-pytest-anti-padroes.md`.

Ao gerar ou aceitar testes, **nunca** produza nem aprove:

## Estrutura

- ❌ Comentários `# Arrange`, `# Act`, `# Assert`. A separação por linha em branco já comunica.
- ❌ `if`/`else`/`try-except` para controle de fluxo dentro do teste. Se precisa de `if`, são dois testes.
- ❌ Loops sobre casos de teste com `for`. Use parametrização do framework.
- ❌ Múltiplas chamadas Act no mesmo teste. Cada teste exercita **uma** ação.

## Dependência e isolamento

- ❌ Testes que dependem da ordem de execução.
- ❌ Estado compartilhado entre testes via variáveis de módulo, singletons ou fixtures de escopo grande sem necessidade.
- ❌ `time.sleep()` para sincronização. Use polling com timeout ou injeção de relógio.
- ❌ Acesso à internet pública (DNS, APIs reais) em testes — flaky e lento. Use mocks ou serviços locais.

## Asserções e clareza

- ❌ Asserções genéricas (`assert resultado`, `assert resultado is not None`) quando dá pra ser específico.
- ❌ Testes "espelho" que apenas repetem a implementação (`assert obj.x == obj.x`, `mock.foo(); assert mock.foo.called`).
- ❌ Comparar floats com `==`. Use tolerância (ex: `pytest.approx`).
- ❌ Capturar exceções com `try/except` em vez do mecanismo do framework (`pytest.raises`, `assertRaises`).
- ❌ Asserções soltas no final do teste sem clareza do que cada uma verifica.

## Mocks

- ❌ Mocks em cascata sobre código próprio que poderia ser testado de verdade.
- ❌ Mockar `datetime.datetime.now` diretamente. Use injeção de relógio ou freezing.
- ❌ Mockar bibliotecas de terceiros sem ter uma interface fina sua entre o app e a biblioteca.
- ❌ Asserções vagas de mock (`assert mock.called`) em vez de `assert_called_once_with(...)`.
- ❌ Mockar `__init__` ou métodos mágicos para enganar o teste.

## DRY exagerado

- ❌ Helpers que escondem a parte interessante do teste (ex: `executar_cenario_completo()` fazendo Arrange + Act).
- ❌ Helpers com flags (`helper(do_login=True, criar_pedido=False)`) — cada combinação deveria ser um teste explícito.
- ❌ Constantes globais opacas (`USUARIO_VALIDO`, `DADOS_PADRAO`) no lugar de valores literais quando o valor importa pro cenário.
- ❌ Fixtures que executam o Act do teste — o Act sempre fica visível no corpo.
- ❌ Cadeias longas de fixtures dependentes — abrir um teste vira leitura de 5 arquivos.

## Nomenclatura

- ❌ `test_login`, `test_1`, `test_user_works`, `test_funciona`. Nomes precisam de cenário + comportamento esperado.
- ❌ Nomes referindo a issue/bug ID (`test_fix_bug_1234`) — descreva o comportamento, não a história.
- ❌ `def test_X():` quando há uma classe `TestX` — duplicação de prefixo.

## Cobertura/escopo

- ❌ Testar duas regras de negócio diferentes no mesmo teste só pra "economizar setup". Faça duas funções.
- ❌ Cobertura à custa de testes vazios (`def test_imports_module(): import meu_modulo`).
- ❌ Testar implementação interna (ordem de chamadas, atributos privados) em vez de comportamento.
- ❌ Testes só de "happy path", sem verificar caminhos de erro.

## Performance e flakiness

- ❌ Testes que rodam por segundos sem necessidade — corte ou marque como `slow`.
- ❌ Testes que falham intermitentemente sem investigação ("rodar de novo costuma passar").
- ❌ Dependências entre testes que rodam em paralelo (race conditions silenciosas).
- ❌ Recursos compartilhados (arquivo temporário, porta) sem isolamento por teste.

## Bordas do sistema

- ❌ Teste unitário fazendo I/O real (DB, rede). É teste de integração ou design ruim.
- ❌ Teste e2e validando regra de domínio que deveria estar em unitário.
- ❌ Teste de integração mockando o que deveria ser real (DB falso quando o ponto é validar o SQL).

## Manutenção

- ❌ Comentários óbvios em testes (`# cria um cliente` antes de `cliente = Cliente(...)`).
- ❌ Testes pulados (`@skip`) há semanas sem motivo documentado e prazo de remoção.
- ❌ Testes comentados deixados no repo. Use Git.
- ❌ `# TODO: fazer este teste passar` em código mergado.
