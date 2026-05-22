---
apply: by model decision
instructions: Apply when handling external dependencies in tests, deciding what to mock, or dealing with time/randomness in tests, regardless of framework.
---

# Testes — Isolamento e Mocks (Conceito)

> **Aplica-se quando**: lidando com dependências externas em testes, decidindo o que mockar, ou tratando tempo/randomização. Ferramentas específicas (`pytest-mock`, `freezegun`) ficam em arquivos próprios.

## Isolamento

- **Cada teste é independente.** Nenhum teste depende da ordem de execução nem de estado deixado por outro.
- **Sem estado global compartilhado** entre testes. Use fixtures com escopo função por padrão.
- Se um teste depende de estado, o estado vem **explicitamente via fixture/setup**, não de variáveis de módulo ou singletons.
- Testes devem rodar **em qualquer ordem** e **em paralelo** sem afetar uns aos outros.

## Onde mockar — nos limites do sistema

**Mocke nos limites do sistema**, não internamente:

- ✅ **Bibliotecas que falam com o mundo externo**: HTTP clients, S3, Redis, fila, e-mail.
- ✅ **Funções do Python que dependem do ambiente**: `datetime.now`, `random`, `os.environ`, leitura de arquivos.
- ❌ **Funções internas suas** que poderiam ser testadas de verdade — sinal de design ruim ou teste ruim.
- ❌ **Métodos privados** (`_calcular_taxa`) do código sob teste.

A regra prática: **mock toca o que sai do processo**, não o que mora dentro.

## Tempo: nunca dependa do relógio diretamente

Código que chama `datetime.now()` direto é difícil de testar. Duas estratégias aceitáveis, em ordem de preferência:

### 1. Injeção de relógio (preferido)

A função recebe `now` ou `clock` como parâmetro com default:

```python
def calcular_vencimento(criado_em: datetime, agora: datetime | None = None) -> datetime:
    agora = agora or datetime.now(UTC)
    ...
```

No teste, passe um valor fixo:

```python
def test_vencimento_em_30_dias():
    criado = datetime(2026, 5, 1, tzinfo=UTC)
    agora = datetime(2026, 5, 15, tzinfo=UTC)

    vencimento = calcular_vencimento(criado, agora=agora)

    assert vencimento == datetime(2026, 5, 31, tzinfo=UTC)
```

### 2. Freezing de tempo

Quando injeção não é prática (código legado, lib externa), use uma biblioteca de freezing (em pytest: `freezegun` — ver `08-pytest-mocks.md`).

**Nunca** mocke `datetime.datetime.now` direto — quebra outras chamadas internas do Python.

## Randomização: injete uma seed ou gerador

Mesmo padrão. Não mocke `random` direto:

```python
def embaralhar(itens: list, rng: random.Random | None = None) -> list:
    rng = rng or random.Random()
    ...
```

Em testes: `embaralhar(itens, rng=random.Random(42))` — determinístico.

## Não mocke o que você não possui

Para APIs externas (gateways de pagamento, AWS, etc.), envolva-as em uma **interface fina sua** (`PagamentoGateway`, `S3Client`) e mocke a sua interface.

Mocks diretos da biblioteca de terceiros viram lixo quando a biblioteca atualiza ou muda o contrato.

```python
# ✅ interface sua
class PagamentoGateway(Protocol):
    def cobrar(self, valor: Decimal, cartao: str) -> str: ...

# no teste, mock simples da sua interface
gateway = Mock(spec=PagamentoGateway)
gateway.cobrar.return_value = "tx_123"

# ❌ mockar a lib direto
mocker.patch("stripe.PaymentIntent.create", return_value={...})
# quebra quando stripe muda o método
```

## Verificação de chamadas

Use o método mais específico possível:

- ✅ `mock.assert_called_once_with(arg=valor)` — chamada exata, uma vez.
- ✅ `mock.assert_not_called()` — nunca foi chamada.
- ❌ `assert mock.called` — vago demais; perde contagem e argumentos.
- ❌ `assert mock.call_count == 1` quando `assert_called_once_with` é mais expressivo.

## Stub vs Mock vs Spy

Conceitualmente:

- **Stub** — devolve valor pré-configurado. Não verifica como foi chamado. Use para **dependências de entrada**.
- **Mock** — verifica como foi chamado. Use quando o **fato de ter sido chamado** é o que está sendo testado.
- **Spy** — wrapper sobre o real, verifica chamadas mas executa o código.

Na prática (Python), a mesma `Mock` faz os três papéis. O que importa é **decidir o papel** antes do teste:

- Estou testando que algo **retorna o valor certo** dado uma entrada? → stub a dependência.
- Estou testando que algo **chama um colaborador corretamente**? → mock + asserções de chamada.

Misturar os dois no mesmo teste sinaliza que o teste verifica mais de uma coisa.

## Quando NÃO mockar

- **Funções puras** — teste com entradas reais; mocks são desnecessários.
- **Estruturas de dados próprias** — instancie a classe; não há razão pra mock.
- **Bibliotecas estáveis e baratas** — `pathlib`, `datetime` (use freezing), `decimal`. Mockar adiciona ruído.

Mock excessivo gera testes que validam **a implementação**, não o **comportamento**. Reescrever a implementação quebra os testes mesmo sem mudar o comportamento — sinal de testes ruins.
