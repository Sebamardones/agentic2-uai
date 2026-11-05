"""Grafo del agente router: enruta mensajes del chat de ecommerce a
preventa, postventa o respuesta genérica. Los destinos son cascarones."""

import os
from typing import Literal

from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field
from typing_extensions import Annotated, TypedDict
from langgraph.graph.message import add_messages

from src.router.prompts import POSTVENTA_PROMPT, PREVENTA_PROMPT, ROUTER_PROMPT

load_dotenv()

MODELO = os.getenv("MODELO", "gemini-3.5-flash-lite")


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
    return ChatGoogleGenerativeAI(model=MODELO, temperature=0)


def nodo_router(state: RouterState) -> dict:
    llm = _llm().with_structured_output(Decision)
    decision = llm.invoke(ROUTER_PROMPT.format(mensaje=state["mensaje"]))
    return {
        "ruta": decision.ruta,
        "motivo": decision.motivo,
        "messages": [AIMessage(content=decision.motivo)],
    }


def nodo_preventa(state: RouterState) -> dict:
    respuesta = _llm().invoke(PREVENTA_PROMPT.format(mensaje=state["mensaje"]))
    return {"respuesta": respuesta.text}


def nodo_postventa(state: RouterState) -> dict:
    respuesta = _llm().invoke(POSTVENTA_PROMPT.format(mensaje=state["mensaje"]))
    return {"respuesta": respuesta.text}


def nodo_generica(state: RouterState) -> dict:
    return {
        "respuesta": (
            "Hola, este chat es exclusivo para la tienda; "
            "con gusto te ayudo con productos, compras o pedidos."
        )
    }


def _siguiente_nodo(state: RouterState) -> str:
    return state["ruta"]


def construir_graph():
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

    return builder.compile(checkpointer=MemorySaver())


def diagrama_mermaid() -> str:
    return construir_graph().get_graph().draw_mermaid()
