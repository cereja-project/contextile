# {{LIBRARY_NAME}}

Template base para bibliotecas Python publicadas no [PyPI](https://pypi.org), já configurado para testes automáticos, publicação, documentação via Sphinx e Read the Docs.

## Visão Geral da Arquitetura

```mermaid
graph TD
    User[Usuário]
    Package[{{LIBRARY_NAME}}]
    API[API Pública]
    Core[Módulo Central]
    Utils[Utils]
    Tests[Testes]
    Docs[Documentação]

    User -->|Instalação e Uso| Package
    Package --> API
    API --> Core
    API --> Utils
    Core --> Utils
    Package --> Tests
    Package --> Docs
```

## Instalação

```bash
pip install {{LIBRARY_NAME}}
```

## Uso Básico

```python
from package_name import example_function

result = example_function()
print(result)
```

## Documentação

Acesse a [documentação completa aqui]({{DOCS_URL}}).

## Contribuindo

Contribuições são bem-vindas! Veja `CONTRIBUTING.md`.

## Licença

Licença {{LICENSE_TYPE}}.