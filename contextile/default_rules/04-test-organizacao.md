---
apply: by model decision
instructions: Apply when organizing test files and folders, deciding whether something should be tested, or designing the testing strategy of a project.
---

# Testes — Organização e Escopo

> **Aplica-se quando**: organizando arquivos e pastas de teste, decidindo se algo deve ou não ser testado, ou estruturando a estratégia de testes do projeto. Detalhes de framework (markers, descoberta) ficam em arquivos próprios.

## Pirâmide de testes

Mantenha a proporção: **muitos unitários, menos integração, poucos e2e**.

```
       /\
      /e2e\        poucos, lentos, frágeis — fluxos críticos ponta-a-ponta
     /------\
    /integr. \    quantidade média — adaptadores, repositórios, integrações
   /----------\
  /  unidade   \  muitos, rápidos, focados — regra de negócio pura
 /--------------\
```

Sintomas de pirâmide errada:

- **Muita integração e pouco unitário** — design acoplado demais; lógica espalhada entre camadas.
- **Muito e2e e pouco unitário** — testes lentos, flaky, debugging difícil.
- **Só unitário** — bugs de integração escapam (contratos errados entre camadas).

## Tipos de teste

| Tipo          | Escopo                                                                          | Velocidade |
| ------------- | ------------------------------------------------------------------------------- | ---------- |
| **Unitário**  | Uma função/classe, sem I/O. Mocka colaboradores quando precisa.                | Milissegundos. |
| **Integração**| Múltiplos componentes juntos. Pode usar DB real, fila real (em container).     | Centenas de ms. |
| **E2E**       | Fluxo completo pela API HTTP. Aproxima do uso real.                            | Segundos. |
| **Contrato**  | Verifica contratos entre serviços (ex: schema OpenAPI). Opcional.              | Variável. |

## Estrutura de pastas

```
projeto/
├── src/meu_app/
└── tests/
    ├── conftest.py            # fixtures globais (framework-específico)
    ├── unit/
    │   ├── conftest.py
    │   └── test_*.py
    ├── integration/
    │   └── test_*.py
    ├── e2e/
    │   └── test_*.py
    └── fixtures/              # factories, dados estáticos, helpers compartilhados
        ├── factories.py
        └── data/
```

- Cada tipo de teste em sua pasta — permite rodar separadamente (unit no PR, e2e em CI noturno).
- Mirror do código: `src/meu_app/dominio/pedido.py` → `tests/unit/dominio/test_pedido.py`.
- `fixtures/` para artefatos compartilhados — separa "código de teste" do "infra de teste".

## Convenções de nome

- **Arquivos**: `test_<modulo>.py` (espelha o módulo testado quando possível).
- **Funções**: `test_*`.
- **Classes** (opcional, só para agrupar): `Test<Algo>`.

## O que NÃO testar

- **Detalhes de implementação** — teste comportamento observável (entrada → saída ou efeito), não atributos privados nem ordem de chamadas internas.
- **Bibliotecas de terceiros** — confie que `requests`, `pydantic`, etc., já são testados. Teste **sua integração** com elas, não as libs.
- **Getters/setters triviais** sem lógica.
- **Código gerado** (migrações automáticas, stubs de protobuf, código de boilerplate de ORM).
- **Métodos privados** (`_foo`) diretamente — teste-os pelo método público que os usa. Se um método privado é complexo o suficiente para merecer teste próprio, talvez devesse ser uma função pública em outro módulo.

## Cobertura: critério, não meta

Cobertura mede o **óbvio** (linhas executadas em algum teste), não o **importante** (cenários relevantes cobertos):

- Cobertura **alta + testes ruins** é pior que cobertura média + testes bons. Testes vazios ou que só importam o módulo dão cobertura sem valor.
- Não persiga 100%. Persiga **cobertura dos caminhos críticos** + **caminhos de erro**.
- Faixa saudável de cobertura para a maioria dos projetos: **70-90%**, com o foco no que importa.

Use cobertura como **mapa de calor** de áreas não testadas, não como métrica de qualidade.

## Quando criar teste vs quando não criar

**Crie teste** quando:

- Implementa nova regra de negócio.
- Corrige bug (teste primeiro reproduz, depois corrige).
- Refatora código sem testes — adicione antes de mudar.
- Caminho de erro/exceção tem comportamento específico (ex: rollback, logging).

**Não crie teste** (ou crie mínimo) quando:

- Código é trivial e óbvio (getter, glue code).
- Lógica está em biblioteca de terceiros que já tem testes.
- Cenário é cosmético (formatação de string sem regra).

## Independência entre tipos

- **Unit** pode rodar em qualquer máquina, sem dependências externas. Sem rede, sem DB.
- **Integração** roda contra serviços reais — em container local (Testcontainers) ou ambiente de CI dedicado.
- **E2E** roda contra app completo subido.

Cada tipo tem sua estratégia de **setup/teardown** apropriada. Misturar (teste unitário que faz I/O real) é cheiro de design ruim.

## Execução seletiva

Configure marcadores/tags no framework para rodar subconjuntos:

```
# pseudo-comandos
test --only=unit
test --skip=slow
test --only=integration
```

CI típico:

- **Em cada PR**: unit + integration rápido. Total < 5 min.
- **Antes de merge**: + e2e em ambiente staging. Total < 30 min.
- **Diário**: + testes lentos, smoke em produção, contratos.

## Anti-padrões

- ❌ Pasta única para todos os testes — impede execução seletiva.
- ❌ Todos os testes lentos (integração/e2e) sem marcação de skip.
- ❌ Testes que precisam de internet pública para passar.
- ❌ Mock pesado em testes que deveriam ser de integração.
- ❌ Teste sem decisão clara de qual tipo é (mistura unit + integration na mesma função).
- ❌ Reaproveitar testes e2e para validar regras de domínio (lento demais).
- ❌ Perseguir 100% de cobertura à custa de testes vazios/ruins.
