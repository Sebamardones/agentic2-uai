"""Evalúa el router contra tests/casos_router.json y muestra una tabla.

Uso (desde la raiz del proyecto):
    .venv\\Scripts\\python.exe -X utf8 scripts/test_router.py
"""

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # acentos en Windows

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.router.graph import construir_graph
CASOS = json.loads(
    (RAIZ / "tests" / "casos_router.json").read_text(encoding="utf-8")
)


def main() -> None:
    graph = construir_graph()
    fallos = []

    print(f"{'mensaje':<55} {'esperado':<10} {'obtenido':<10} ok   motivo")
    print("-" * 125)
    for i, caso in enumerate(CASOS):
        config = {"configurable": {"thread_id": f"script-{i}"}}
        estado = graph.invoke({"mensaje": caso["mensaje"]}, config)
        obtenido = estado["ruta"]
        ok = obtenido == caso["esperado"]
        if not ok:
            fallos.append(caso)
        marca = "✔" if ok else "✘"
        print(
            f"{caso['mensaje']:<55} {caso['esperado']:<10} {obtenido:<10} "
            f"{marca}    {estado['motivo']}"
        )

    total = len(CASOS)
    aciertos = total - len(fallos)
    print("-" * 125)
    print(f"Aciertos: {aciertos}/{total} ({aciertos / total:.0%})")
    if fallos:
        print("Fallados:")
        for caso in fallos:
            print(f"  - {caso['mensaje']} (esperado: {caso['esperado']})")
    else:
        print("Sin fallos.")


if __name__ == "__main__":
    main()
