"""Grafo del agente router: enruta mensajes del chat de ecommerce a
preventa, postventa o respuesta genérica. Los destinos son cascarones."""

import logging
import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field
from typing_extensions import Annotated, TypedDict
from langgraph.graph.message import add_messages

from src.router.prompts import (
    GENERICA_PROMPT,
    POSTVENTA_PROMPT,
    PREVENTA_PROMPT,
    ROUTER_PROMPT,
)
from src.router.tools import abrir_memoria

load_dotenv()

MODELO = os.getenv("MODELO", "gemini-3.5-flash-lite")
CONTEXTO_TIENDA = (
    Path(__file__).resolve().parents[2] / "data" / "tienda.md"
).read_text(encoding="utf-8")
RESPUESTA_GENERICA_FALLBACK = (
    "Hola, este chat es exclusivo para la tienda; "
    "con gusto te ayudo con productos, compras o pedidos."
)
logger = logging.getLogger("router.graph")


class Decision(BaseModel):
    ruta: Literal["preventa", "postventa", "generica"] = Field(
        description="A qué agente va el mensaje."
    )
    motivo: str = Field(description="Una frase: por qué esa ruta.")


class RouterState(TypedDict):
    mensaje: str
    ruta: str
    motivo: str
    respuesta: str
    messages: Annotated[list, add_messages]


def _llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model=MODELO)


def nodo_router(state: RouterState) -> dict:
    llm = _llm().with_structured_output(Decision)
    decision = llm.invoke(ROUTER_PROMPT.format(mensaje=state["mensaje"]))
    return {
        "ruta": decision.ruta,
        "motivo": decision.motivo,
        "messages": [HumanMessage(content=state["mensaje"])],
    }


def nodo_preventa(state: RouterState) -> dict:
    respuesta = _llm().invoke(PREVENTA_PROMPT.format(mensaje=state["mensaje"]))
    return {
        "respuesta": respuesta.text,
        "messages": [AIMessage(content=respuesta.text)],
    }


def nodo_postventa(state: RouterState) -> dict:
    respuesta = _llm().invoke(POSTVENTA_PROMPT.format(mensaje=state["mensaje"]))
    return {
        "respuesta": respuesta.text,
        "messages": [AIMessage(content=respuesta.text)],
    }


def nodo_generica(state: RouterState) -> dict:
    historial = state.get("messages") or [HumanMessage(content=state["mensaje"])]
    mensajes = [
        SystemMessage(content=GENERICA_PROMPT.format(tienda=CONTEXTO_TIENDA)),
        *historial,
    ]
    try:
        respuesta = _llm().invoke(mensajes).text
    except Exception:
        logger.exception("El modelo falló en la ruta genérica; se usa el fallback.")
        respuesta = RESPUESTA_GENERICA_FALLBACK
    return {"respuesta": respuesta, "messages": [AIMessage(content=respuesta)]}


def _siguiente_nodo(state: RouterState) -> str:
    return state["ruta"]


def construir_graph(checkpointer: BaseCheckpointSaver | None = None):
    builder = StateGraph(RouterState)
    builder.add_node("router", nodo_router)
    builder.add_node("agente_preventa", nodo_preventa)
    builder.add_node("agente_postventa", nodo_postventa)
    builder.add_node("respuesta_generica", nodo_generica)

    builder.set_entry_point("router")
    builder.add_conditional_edges(
        "router", _siguiente_nodo, {
            "preventa": "agente_preventa",
            "postventa": "agente_postventa",
            "generica": "respuesta_generica",
        }
    )
    builder.add_edge("agente_preventa", END)
    builder.add_edge("agente_postventa", END)
    builder.add_edge("respuesta_generica", END)

    return builder.compile(checkpointer=checkpointer or MemorySaver())


def diagrama_mermaid() -> str:
    return construir_graph().get_graph().draw_mermaid()
