"""Pruebas de selección y fallback de la memoria del router."""

from src.router import tools


def test_sin_database_url_usa_ram(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with tools.abrir_memoria() as memoria:
        assert memoria.tipo == "ram"


def test_postgres_no_disponible_usa_ram(monkeypatch):
    class PoolFallido:
        check_connection = object()

        def __init__(self, **kwargs):
            pass

        def open(self, **kwargs):
            raise OSError("base no disponible")

        def close(self):
            pass

    monkeypatch.setenv("DATABASE_URL", "postgresql://db-inexistente/prueba")
    monkeypatch.setattr(tools, "ConnectionPool", PoolFallido)

    with tools.abrir_memoria() as memoria:
        assert memoria.tipo == "ram"
