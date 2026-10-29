"""Fixtures partilhadas por todos os testes do projeto."""
import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _limpar_cache():
    """O throttling guarda os contadores de tentativas na cache.

    Sem isto, as tentativas de login de um teste contavam para o seguinte e o
    limite de 10/minuto disparava a meio da suite. Cada teste começa do zero.
    """
    cache.clear()
    yield
    cache.clear()