"""CLI principal: ejecuta agentes de src/{nombre}/ desde la raíz.

Uso:
    python main.py {nombre_agente} "mensaje"
    python main.py router "¿tienen stock?" --saltos
    python main.py router --diagrama
"""

import argparse
import importlib
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Ejecuta un agente de src/.")
    parser.add_argument("agente", help="Nombre del agente (carpeta en src/).")
    parser.add_argument("mensaje", nargs="?", default=None, help="Mensaje del usuario.")
    parser.add_argument("--saltos", action="store_true",
                        help="Imprime los nodos por los que pasó el grafo.")
    parser.add_argument("--diagrama", action="store_true",
                        help="Imprime el Mermaid del grafo sin ejecutarlo.")
    parser.add_argument("--thread-id", default="cli", help="ID de hilo para la memoria.")
    args = parser.parse_args()

    try:
        graph_mod = importlib.import_module(f"src.{args.agente}.graph")
    except ModuleNotFoundError:
        print(f"Error: no existe src/{args.agente}/graph.py", file=sys.stderr)
        sys.exit(1)

    if args.diagrama:
        print(graph_mod.diagrama_mermaid())
        return

    if args.mensaje is None:
        print("Error: falta el mensaje (o usa --diagrama).", file=sys.stderr)
        sys.exit(1)

    graph = graph_mod.construir_graph()
    config = {"configurable": {"thread_id": args.thread_id}}

    if args.saltos:
        saltos = []
        for chunk in graph.stream(
            {"mensaje": args.mensaje}, config, stream_mode="updates"
        ):
            saltos.extend(chunk.keys())
        estado = graph.get_state(config).values
        print(" → ".join(saltos))
        print(f"Motivo: {estado['motivo']}")
        print(f"Respuesta: {estado['respuesta']}")
    else:
        estado = graph.invoke({"mensaje": args.mensaje}, config)
        print(estado["respuesta"])


if __name__ == "__main__":
    main()
