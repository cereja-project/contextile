---
apply: by model decision
instructions: Apply when organizing imports, creating new modules, setting up `__init__.py`, or resolving circular imports.
---

# Python — Imports e Módulos

> **Aplica-se quando**: organizando imports, criando módulos novos, decidindo o que expor em `__init__.py`, ou lidando com imports circulares.

## Sempre imports absolutos

```python
# ✅ absoluto
from meu_app.dominio.pedido import Pedido
from meu_app.infra.db import Session

# ❌ relativo
from .dominio.pedido import Pedido
from ..infra.db import Session
```

Imports absolutos sobrevivem a refatorações (mover arquivo não quebra os outros). Relativos só fazem sentido em pacotes que serão distribuídos como biblioteca standalone.

## Ordem (ruff/isort cuida)

Três blocos, separados por linha em branco, na ordem:

1. **Stdlib** — `os`, `sys`, `pathlib`, `datetime`, etc.
2. **Terceiros** — `fastapi`, `sqlalchemy`, `pydantic`, etc.
3. **Local** — `meu_app.*`.

```python
import logging
from datetime import datetime
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from meu_app.dominio.pedido import Pedido
from meu_app.infra.db import get_session
```

Não ordene manualmente — configure ruff (`select = ["I"]` cobre isort) e rode no save.

## Estilo dos imports

```python
# ✅ um por linha quando vários do mesmo módulo
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
    selectinload,
)

# ✅ direto quando é um só
from sqlalchemy import select

# ❌ wildcard
from sqlalchemy import *
```

`from X import *` é proibido — pollui namespace, esconde origem dos símbolos, quebra ferramentas de análise.

## Alias só quando necessário

```python
# ✅ alias convencional
import numpy as np
import pandas as pd

# ✅ alias para evitar conflito
from meu_app.dominio import Cliente as ClienteDominio
from meu_app.dto import Cliente as ClienteDto

# ❌ alias gratuito
from datetime import datetime as dt
```

## Imports lazy (dentro de função) — apenas em casos específicos

Use só para:

- **Quebrar circular import** (último recurso, prefira refatorar).
- **Dependência opcional** (lib pesada usada em código pouco chamado).
- **Lazy loading** comprovado por perfilação (raríssimo).

```python
def gerar_relatorio_pdf(pedido: Pedido) -> bytes:
    from reportlab.pdfgen import canvas  # lib pesada, só usada aqui
    ...
```

Em todos os outros casos, import vai no topo do módulo.

## Imports circulares

São cheiro de design ruim — quase sempre resolvidos por refatoração:

1. **Extrair tipo compartilhado** para módulo separado (ex: `interfaces.py`, `types.py`).
2. **Inverter dependência** — o módulo mais "baixo" não deve importar do "alto".
3. **Type-only import** com `TYPE_CHECKING` para anotações:
   ```python
   from typing import TYPE_CHECKING
   if TYPE_CHECKING:
       from meu_app.servicos.pedido import PedidoService
   ```
   Isso evita o ciclo em runtime e ainda dá tipo correto pro checker.

Imports lazy dentro de função são plano D, não plano A.

## `__init__.py` — papel e regras

### O que `__init__.py` faz

- Marca a pasta como pacote Python (em Python 3.3+ não é mais obrigatório, mas mantenha por compatibilidade e clareza).
- **Define a API pública** do pacote.

### Regras

1. `__init__.py` **não faz trabalho** (sem queries, sem I/O, sem efeitos colaterais). Apenas reexporta.
2. **Exponha apenas o que é público**:
   ```python
   # meu_app/dominio/__init__.py
   from meu_app.dominio.pedido import Pedido, PedidoStatus
   from meu_app.dominio.cliente import Cliente, TipoCliente

   __all__ = [
       "Cliente",
       "Pedido",
       "PedidoStatus",
       "TipoCliente",
   ]
   ```
3. **Use `__all__`** para declarar a API pública explicitamente. Sem `__all__`, `from pacote import *` pega tudo que não começa com `_` — incluindo imports internos.
4. Em pacotes grandes, `__init__.py` vazio também é válido — força callers a importar do módulo específico (`from meu_app.dominio.pedido import Pedido`).

## Estrutura de pacotes (alto nível)

Organize por **camada e domínio**, não por tipo:

```
src/meu_app/
├── dominio/              # entidades, regras de negócio (sem I/O)
│   ├── pedido.py
│   └── cliente.py
├── aplicacao/            # casos de uso, orquestração
│   └── checkout.py
├── infra/                # adaptadores: DB, HTTP, fila
│   ├── db.py
│   └── pagamento_gateway.py
└── api/                  # entrada HTTP (FastAPI, etc.)
    └── routers/
```

Evite estrutura por tipo (`models/`, `services/`, `helpers/`) — força conhecer o sistema todo para mexer numa feature.

## Imports em scripts e notebooks

Em scripts entrypoint (`__main__.py`, `cli.py`), o import pode ser mais permissivo. Em **código de biblioteca/aplicação**, siga todas as regras acima estritamente.
