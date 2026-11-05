"""Pruebas del agente router.

- Unitarias: no usan el modelo.
- test_ruta (parametrizado): enruta los casos de casos_router.json con la
  API real; no afirma caso a caso, solo acumula fallos.
- test_umbral_minimo: exige al menos 13 de 15 aciertos (el modelo no es
  determinista). Se salta todo si no hay GOOGLE_API_KEY.
"""

import json
import os
from pathlib import Path

import pytest

from src.router.graph import (
    Decision,
    construir_graph,
    diagrama_mermaid,
    nodo_generica,
)

CASOS = json.loads(
    (Path(__file__).parent / "casos_router.json").read_text(encoding="utf-8")
)

requiere_api = pytest.mark.skipif(
    not os.getenv("GOOGLE_API_KEY"), reason="sin GOOGLE_API_KEY"
)


def test_decision_rutas_validas():
    decision = Decision(ruta="preventa", motivo="pregunta por stock")
    assert decision.ruta == "preventa"
    assert decision.motivo


def test_decision_rechaza_ruta_invalida():
    with pytest.raises(ValueError):
        Decision(ruta="ventas", motivo="no existe esa ruta")


def test_nodo_generica_no_usa_modelo():
    estado = nodo_generica({"mensaje": "¿qué hora es en Tokio?"})
    assert "tienda" in estado["respuesta"]


def test_diagrama_contiene_nodos():
    mermaid = diagrama_mermaid()
    for nodo in ("router", "agente_preventa", "agente_postventa", "respuesta_generica"):
        assert nodo in mermaid


_graph = None
_fallos = []


def _get_graph():
    global _graph
    if _graph is None:
        _graph = construir_graph()
    return _graph


@requiere_api
@pytest.mark.parametrize("caso", CASOS, ids=[c["mensaje"] for c in CASOS])
def test_ruta(caso):
    estado = _get_graph().invoke(
        {"mensaje": caso["mensaje"]},
        {"configurable": {"thread_id": f"pytest-{caso['mensaje']}"}},
    )
    if estado["ruta"] != caso["esperado"]:
        _fallos.append((caso["mensaje"], caso["esperado"], estado["ruta"]))


@requiere_api
def test_umbral_minimo():
    max_fallos = len(CASOS) - 13
    assert len(_fallos) <= max_fallos, f"Demasiados fallos: {_fallos}"
