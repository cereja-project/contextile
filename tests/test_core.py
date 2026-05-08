"""Testes para o módulo core."""

import pytest
from package_name.core import example_function

def test_example_function():
    """Testa se example_function retorna a mensagem correta."""
    assert example_function() == "Olá do core!"