---
apply: by model decision
instructions: Apply when handling concurrency or parallelism in Python — choosing between threading, multiprocessing, or concurrent.futures; using synchronization primitives, queues, or calling subprocess.
---

# Python — Concorrência e Paralelismo

> **Aplica-se quando**: lidando com concorrência ou paralelismo em Python 3.12+ — escolhendo entre threading, multiprocessing, concurrent.futures, ou primitivas de sincronização. Para asyncio em detalhe, ver `19-python-async.md`.

## Os três modelos em Python

Cada modelo serve um caso de uso diferente. **Escolher o errado custa caro** — threads em trabalho CPU bound não aceleram nada; processos em I/O leve custam mais que economizam.

| Modelo            | Paralelismo real? | I/O bound | CPU bound | Custo                                |
| ----------------- | ----------------- | --------- | --------- | ------------------------------------ |
| **asyncio**       | Não (1 thread)    | ✅ ótimo  | ❌ ruim    | Baixo; precisa libs async            |
| **threading**     | Não (GIL)         | ✅ bom    | ❌ ruim    | Médio; concorrência cooperativa      |
| **multiprocessing** | ✅ sim          | Médio     | ✅ ótimo  | Alto; serialização, fork, IPC        |

## GIL — por que importa

CPython tem o **Global Interpreter Lock**: apenas uma thread executa bytecode Python por vez no mesmo processo. Implicações:

- **Threads não paralelizam código Python puro** — não use threads esperando aceleração CPU bound.
- Threads **liberam o GIL durante I/O** (rede, disco, syscalls), então funcionam bem pra I/O bound.
- Operações em **bibliotecas C otimizadas** (NumPy, lxml, criptografia) frequentemente liberam o GIL durante o trabalho pesado — threads aceleram nesses casos.
- **Multiprocessing** contorna o GIL: cada processo tem seu próprio interpretador.

### Olho no horizonte (3.13+)

- **PEP 703 — free-threaded CPython** (sem GIL) — experimental no 3.13, ainda não default. Não dependa em produção 3.12.
- **PEP 734 — `concurrent.interpreters`** — múltiplos interpretadores no mesmo processo, cada um com seu GIL. API estável a partir do 3.14. Em 3.12-3.13, evite (API mudou).

Em 3.12, **assuma GIL e use multiprocessing para CPU bound**.

## Árvore de decisão

1. **É I/O bound (rede, disco, DB)?**
   - Codebase async first → `asyncio` (`19-python-async.md`).
   - Codebase sync, libs sync → `threading` ou `concurrent.futures.ThreadPoolExecutor`.

2. **É CPU bound?**
   - Trabalho pesado (segundos+) → `multiprocessing` ou `concurrent.futures.ProcessPoolExecutor`.
   - Lib C que libera GIL (NumPy, criptografia) → threads funcionam.
   - Trabalho muito pesado e contínuo → worker dedicado (Celery, RQ), não dentro do processo principal.

3. **Mistura?**
   - I/O com pedaços CPU bound → async/threads + `asyncio.to_thread` ou pool de processos para o pedaço CPU.

4. **Sequencial seria rápido o suficiente?**
   - **Não adicione concorrência.** Mede primeiro. Concorrência adiciona complexidade, bugs sutis, e debug difícil.

## `concurrent.futures` — API preferida

Para 90% dos casos, **use `concurrent.futures` em vez de `threading.Thread` ou `multiprocessing.Process` direto**. API uniforme, error handling decente, context manager para cleanup.

### `ThreadPoolExecutor` — I/O bound

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def baixar(url: str) -> bytes:
    return requests.get(url, timeout=10).content

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(baixar, url): url for url in urls}

    for future in as_completed(futures):
        url = futures[future]
        try:
            conteudo = future.result()
            processar(url, conteudo)
        except Exception:
            logger.exception("falha em %s", url)
```

Pontos importantes:

- **`max_workers`** dimensionado pelo recurso limitante (banda, conexões externas, não CPU).
- **`as_completed`** para processar resultados conforme chegam.
- **`future.result()` dentro de `try`** — exceções da tarefa são reerguidas aqui.
- **Context manager** garante shutdown limpo (espera tarefas terminarem).

### `ProcessPoolExecutor` — CPU bound

```python
from concurrent.futures import ProcessPoolExecutor

def processar_imagem(caminho: Path) -> Path:
    # trabalho CPU bound: redimensionar, comprimir, etc.
    ...

with ProcessPoolExecutor() as executor:
    resultados = list(executor.map(processar_imagem, caminhos))
```

- **Sem `max_workers`** = `os.process_cpu_count()` (3.13+) ou `os.cpu_count()`. Geralmente o default está ok.
- **`executor.map`** preserva ordem; **`submit` + `as_completed`** dá os primeiros que terminam.
- **Argumentos e retornos** devem ser **picklable** — funções, classes, dataclasses simples sim; closures, lambdas, conexões abertas, não.

### `executor.map` com timeout e tratamento

```python
with ProcessPoolExecutor() as executor:
    for entrada, resultado in zip(entradas, executor.map(funcao, entradas, timeout=60)):
        ...
```

`timeout` é por **iteração**, não total. Para timeout global, use `as_completed(futures, timeout=N)`.

## `threading` — quando ainda usar diretamente

Use `threading.Thread` direto **só** quando:

- Precisa de **thread daemon** rodando indefinidamente (poll, listener).
- Precisa controle fino de lifecycle (start, join manual, evento de parada).

Para "rodar N funções em paralelo", **use `ThreadPoolExecutor`**.

### Padrão de thread daemon com parada limpa

```python
import threading

_parar = threading.Event()

def consumidor() -> None:
    while not _parar.is_set():
        try:
            mensagem = fila.get(timeout=1)
        except queue.Empty:
            continue
        processar(mensagem)

worker = threading.Thread(target=consumidor, daemon=True)
worker.start()

# em shutdown:
_parar.set()
worker.join(timeout=5)
```

- **`daemon=True`** — thread morre quando o programa termina. Sem isso, programa não encerra até a thread terminar.
- **Sempre `Event` para parada** — nunca `while True` sem saída.
- **`join(timeout=...)`** — não bloqueie indefinidamente no shutdown.

## Primitivas de sincronização (threading)

Compartilhar estado entre threads sem sincronização é fonte certeira de bugs (race conditions, dados corrompidos). **Sempre use as primitivas como context manager**.

### `Lock` — exclusão mútua

```python
import threading

_lock = threading.Lock()
_saldo = 0

def depositar(valor: int) -> None:
    global _saldo
    with _lock:                 # ✅ sempre como context manager
        _saldo += valor
```

### `RLock` — re-entrant lock

Permite que a **mesma thread** adquira o lock múltiplas vezes (útil em métodos que chamam outros métodos do mesmo objeto que também precisam do lock).

### `Semaphore` — limitar concorrência

```python
_max_conexoes = threading.BoundedSemaphore(value=10)

def chamar_api(url: str) -> dict:
    with _max_conexoes:         # máximo 10 simultâneas
        return requests.get(url, timeout=5).json()
```

Use **`BoundedSemaphore`** (não `Semaphore`) — detecta `release()` em excesso (bug clássico).

### `Event` — sinalização one-shot

```python
pronto = threading.Event()

# thread A
pronto.wait()                   # bloqueia até set()
# thread B
pronto.set()                    # libera A
```

Bom para "esperar inicialização", "sinal de shutdown".

### `Condition` — espera com predicado

Para padrões produtor-consumidor mais complexos. Quase sempre, `queue.Queue` é mais simples e seguro.

### `Barrier` — sincronização N-way

Espera N threads chegarem antes de todas continuarem. Raramente útil fora de testes ou benchmarks.

## `queue.Queue` — comunicação thread-safe

Para passar dados entre threads, **prefira `queue.Queue` a estado compartilhado com locks**. Mais simples e seguro.

```python
import queue
from threading import Thread

fila: queue.Queue[Tarefa] = queue.Queue(maxsize=100)

def consumidor() -> None:
    while True:
        tarefa = fila.get()
        if tarefa is None:      # sentinela de fim
            break
        processar(tarefa)
        fila.task_done()

# produtor
for t in tarefas:
    fila.put(t)
fila.put(None)                  # sinaliza fim
fila.join()                     # espera consumidores terminarem
```

- **`maxsize`** evita produtor encher memória se consumidor é lento (backpressure).
- **`task_done()` + `join()`** sincroniza fim.
- **Sentinela `None`** (ou `Queue.shutdown()` no 3.13+) avisa consumidores pra parar.

`queue.SimpleQueue` é alternativa quando você não precisa de `join`/`task_done` — mais leve.

## `multiprocessing` — paralelismo real

Para CPU bound, `multiprocessing` cria processos separados (cada um com seu interpretador Python). Custos a saber:

### Start method

```python
import multiprocessing as mp

if __name__ == "__main__":
    mp.set_start_method("spawn")   # ou "fork" (Linux only, mais rápido mas problemático)
    ...
```

- **`spawn`** (default em macOS 3.8+ e Windows) — novo processo limpo. Mais lento de iniciar; mais seguro.
- **`fork`** (default em Linux antes do 3.14; deprecated em 3.14) — herda estado do pai. Rápido, mas frágil com threads, locks, conexões abertas.
- **`forkserver`** — meio termo.

**Em 3.12+, prefira `spawn` explicitamente** — comportamento consistente entre plataformas e seguro com bibliotecas que usam threads internamente.

### `if __name__ == "__main__"` obrigatório

Com `spawn`, o módulo é reimportado em cada processo filho. Sem o guard, o filho **executa o código do módulo de novo**, criando recursão infinita de processos.

```python
def trabalhar(x: int) -> int: ...

if __name__ == "__main__":
    with ProcessPoolExecutor() as ex:
        resultados = list(ex.map(trabalhar, range(100)))
```

### Argumentos precisam ser picklable

Funções e dados passados aos workers são serializados via `pickle`. Coisas que **não** funcionam:

- Funções lambda, closures, métodos com `self` complexo.
- Conexões de banco, sockets, file handles abertos.
- Classes definidas em `__main__` ou interativamente.

Defina funções no escopo do módulo, top-level. Passe dados simples (números, strings, dataclasses, dicts).

### `multiprocessing.Queue` para comunicação

Igual a `queue.Queue`, mas funciona entre processos. Para volumes grandes, considere `multiprocessing.shared_memory` (memória compartilhada sem cópia).

## `contextvars` — propagação de contexto

Para passar contexto (request ID, user ID, trace) entre funções **sem parâmetros explícitos**, em ambientes sync, async, **e** entre tarefas async:

```python
from contextvars import ContextVar

request_id: ContextVar[str] = ContextVar("request_id", default="-")

# middleware HTTP
request_id.set(req.headers.get("X-Request-ID", str(uuid4())))

# qualquer lugar
logger.info("processando", extra={"request_id": request_id.get()})
```

Vantagens sobre `threading.local`:

- **Funciona em async** (cada task tem sua cópia).
- **Compatível com asyncio** — `asyncio.Task` herda contexto da criação.
- **Funciona em threads** desde 3.7.

Em `concurrent.futures.Executor`, **contextvars NÃO se propaga automaticamente** para os workers. Passe explicitamente ou use wrapper.

## `subprocess` — chamar processos externos

Para executar comandos de SO, **sempre prefira `subprocess.run` à API legada (`os.system`, `os.popen`)**.

```python
import subprocess

result = subprocess.run(
    ["git", "status", "--porcelain"],
    capture_output=True,
    text=True,
    timeout=10,
    check=True,                  # levanta CalledProcessError se sair com !=0
)
print(result.stdout)
```

Regras:

- **`shell=False`** sempre que possível (default). Passe `args` como **lista**, não string.
- **`timeout=...`** obrigatório em qualquer chamada — processo pendurado trava o app.
- **`check=True`** para tratar saída !=0 como erro.
- **`text=True`** (ou `encoding="utf-8"`) — decodifica stdout/stderr em string.
- **Nunca use `shell=True` com input externo** — risco de injeção de comando.

Para pipes complexos, use `subprocess.Popen` com cuidado, ou prefira chamar comandos separados encadeando em Python.

## `sched` — agendamento simples

Para agendamento simples in-process. Para qualquer coisa séria (cron, retries, persistence), use ferramenta externa (Celery beat, APScheduler, etc.).

## Quando NÃO usar concorrência

- Trabalho sequencial é rápido o suficiente.
- A complexidade adicional não compensa o ganho (bugs sutis, debug difícil).
- Não tem perfil mostrando que concorrência ajuda.
- Tarefa única, sem iteração.

**Adicione concorrência sob justificativa medida**, não preventiva.

## Anti-padrões

- ❌ Threads para CPU bound (GIL impede paralelismo real em Python puro).
- ❌ `threading.Thread` direto quando `ThreadPoolExecutor` resolve.
- ❌ `multiprocessing.Process` direto quando `ProcessPoolExecutor` resolve.
- ❌ Compartilhar mutáveis entre threads sem `Lock` (`list.append`, `dict[key] = val` parecem atômicos, mas não são em geral).
- ❌ `while True: ...` em thread daemon sem `Event` para parada.
- ❌ `multiprocessing` em Linux sem `set_start_method("spawn")` — fork com threads é fonte de bugs.
- ❌ `if __name__ == "__main__":` ausente em script que usa `multiprocessing` com `spawn`.
- ❌ Passar lambda, closure, ou objeto não-picklable para `ProcessPoolExecutor`.
- ❌ `subprocess.run(cmd, shell=True)` com input externo.
- ❌ `subprocess.run(...)` sem `timeout`.
- ❌ `time.sleep` em thread para "esperar evento" — use `Event.wait(timeout=...)`.
- ❌ `threading.local` quando `contextvars` resolve (mais portável, async-friendly).
- ❌ Lock global compartilhado por código de bibliotecas diferentes — risco de deadlock.
- ❌ Adquirir lock A e dentro do `with` tentar adquirir lock B em ordens diferentes em código diferente — deadlock clássico. Defina ordem total de aquisição.
- ❌ Adicionar concorrência sem medir ganho.
