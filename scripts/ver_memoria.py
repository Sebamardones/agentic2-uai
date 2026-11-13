"""Lista los hilos persistidos o muestra los mensajes de uno."""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.messages import AIMessage, HumanMessage

from src.router.tools import abrir_memoria


def _rol(mensaje) -> str:
    if isinstance(mensaje, HumanMessage):
        return "usuario"
    if isinstance(mensaje, AIMessage):
        return "asistente"
    return getattr(mensaje, "type", "mensaje")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspecciona la memoria del router.")
    parser.add_argument("thread_id", nargs="?", help="Hilo que se quiere mostrar.")
    args = parser.parse_args()

    with abrir_memoria() as memoria:
        if args.thread_id:
            config = {"configurable": {"thread_id": args.thread_id}}
            checkpoint = next(memoria.checkpointer.list(config, limit=1), None)
            if checkpoint is None:
                print(f"No hay checkpoints para el hilo {args.thread_id!r}.")
                return
            mensajes = checkpoint.checkpoint["channel_values"].get("messages", [])
            if not mensajes:
                print(f"El hilo {args.thread_id!r} no tiene mensajes.")
                return
            for mensaje in mensajes:
                print(f"{_rol(mensaje)}: {mensaje.content}")
            return

        hilos = defaultdict(list)
        for checkpoint in memoria.checkpointer.list(None):
            thread_id = checkpoint.config["configurable"]["thread_id"]
            hilos[thread_id].append(checkpoint)

        if not hilos:
            print(f"No hay hilos guardados en memoria {memoria.tipo}.")
            return

        print(f"{'thread_id':<32} {'checkpoints':>11}  último checkpoint")
        for thread_id, checkpoints in sorted(
            hilos.items(), key=lambda item: item[1][0].checkpoint["ts"], reverse=True
        ):
            print(
                f"{thread_id:<32} {len(checkpoints):>11}  "
                f"{checkpoints[0].checkpoint['ts']}"
            )


if __name__ == "__main__":
    main()
