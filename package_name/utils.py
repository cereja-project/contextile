import os

# Dicionário com os valores das TAGs
tags = {
    "{{LIBRARY_NAME}}": "minha_biblioteca",
    "{{AUTHOR_NAME}}": "João Silva",
    "{{AUTHOR_EMAIL}}": "joao@email.com",
    "{{VERSION}}": "0.1.0",
    "{{SHORT_DESCRIPTION}}": "Biblioteca Python exemplo",
    "{{LICENSE_TYPE}}": "MIT",
    "{{LICENSE_CLASSIFIER}}": "MIT License",
    "{{YEAR}}": "2025",
    "{{GITHUB_URL}}": "https://github.com/jlsneto/minha_biblioteca",
    "{{DOCS_URL}}": "https://minha_biblioteca.readthedocs.io"
}

# Lista de arquivos para substituir as TAGs
FILES = [
    "README.md",
    "pyproject.toml",
    "setup.cfg",
    "MANIFEST.in",
    "LICENSE",
    "docs/conf.py",
    "docs/index.rst",
    "docs/modules.rst",
    ".readthedocs.yml",
    ".github/workflows/ci.yml",
    ".github/workflows/publish.yml",
    "package_name/__init__.py",
    "package_name/core.py",
    "package_name/utils.py",
    "tests/test_core.py"
]

def replace_tags_in_file(file_path, tags):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    for tag, value in tags.items():
        content = content.replace(tag, value)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Tags substituídas em: {file_path}")

def main():
    for file_path in FILES:
        if os.path.exists(file_path):
            replace_tags_in_file(file_path, tags)
        else:
            print(f"Arquivo não encontrado: {file_path}")

    # Sugestão: Renomeie o diretório principal do pacote
    old_dir = "package_name"
    new_dir = tags["{{LIBRARY_NAME}}"]
    if os.path.exists(old_dir):
        os.rename(old_dir, new_dir)
        print(f"Diretório do pacote renomeado para: {new_dir}")

if __name__ == "__main__":
    main()