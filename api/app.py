"""API FastAPI del chat de ecommerce.

El grafo router se compila UNA vez al arrancar la app y se reutiliza en
cada request. Levantar con: uvicorn api.app:app --reload --port 8000
"""

import logging
import os
import secrets
from contextlib import asynccontextmanager
from typing import Literal

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from src.router.graph import construir_graph
from src.router.tools import abrir_memoria

load_dotenv()

MODELO = os.getenv("MODELO", "gemini-3.5-flash-lite")
API_KEY = os.getenv("API_KEY", "")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_SECRET = os.getenv("TELEGRAM_SECRET", "")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api.app")


graph = construir_graph()
TIPO_MEMORIA = "ram"


@asynccontextmanager
async def lifespan(_: FastAPI):
    global graph, TIPO_MEMORIA
    with abrir_memoria() as memoria:
        graph = construir_graph(memoria.checkpointer)
        TIPO_MEMORIA = memoria.tipo
        yield


app = FastAPI(
    title="Ecommerce Router API",
    version="1.0.0",
    description=(
        "API del chat de un ecommerce. El router analiza cada mensaje del "
        "cliente y lo deriva al agente correspondiente. Las tres rutas "
        "posibles son: **preventa** (intención de compra, productos, "
        "precios, stock, promociones, formas de pago), **postventa** "
        "(quejas, seguimiento de pedidos, devoluciones, cambios, "
        "garantías) y **generica** (temas ajenos a la tienda)."
    ),
    lifespan=lifespan,
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class ChatRequest(BaseModel):
    user_id: str = Field(
        description="Identificador del usuario; se usa como thread_id del grafo.",
        examples=["user-123"],
    )
    texto: str = Field(
        description="Mensaje del cliente.",
        examples=["¿tienen la polera azul en talla M?"],
    )


class ChatResponse(BaseModel):
    ruta: Literal["preventa", "postventa", "generica"] = Field(
        description="Agente al que fue derivado el mensaje.",
        examples=["preventa"],
    )
    motivo: str = Field(
        description="Frase que explica por qué el router eligió esa ruta.",
        examples=["El cliente pregunta por stock de un producto antes de comprar."],
    )
    respuesta: str = Field(
        description="Respuesta generada por el agente destino.",
        examples=["Soy el agente de preventa. Recibí: ..."],
    )


@app.get("/health", tags=["salud"])
def health() -> dict:
    """Estado de la API y modelo configurado."""
    return {"ok": True, "modelo": MODELO, "memoria": TIPO_MEMORIA}


@app.post(
    "/chat",
    tags=["chat"],
    response_model=ChatResponse,
    responses={
        200: {
            "description": "Mensaje enrutado correctamente.",
            "model": ChatResponse,
        },
        401: {
            "description": "Falta la cabecera X-API-Key o la clave es inválida.",
        },
        422: {
            "description": "Body inválido: falta user_id o texto, o tienen el tipo incorrecto.",
        },
        502: {
            "description": "El modelo de IA falló al procesar el mensaje; reintentar más tarde.",
        },
    },
)
def chat(
    body: ChatRequest,
    api_key: str | None = Security(api_key_header),
) -> ChatResponse:
    """Enruta el mensaje del cliente al agente correspondiente."""
    if not API_KEY or api_key is None or not secrets.compare_digest(api_key, API_KEY):
        raise HTTPException(
            status_code=401,
            detail="Clave de API ausente o inválida.",
        )

    try:
        estado = graph.invoke(
            {"mensaje": body.texto},
            {"configurable": {"thread_id": body.user_id}},
        )
    except Exception:
        logger.exception(
            "Fallo del modelo al enrutar mensaje de user_id=%s", body.user_id
        )
        raise HTTPException(
            status_code=502,
            detail="El modelo de IA no respondió; inténtalo de nuevo más tarde.",
        )
    return ChatResponse(
        ruta=estado["ruta"],
        motivo=estado["motivo"],
        respuesta=estado["respuesta"],
    )


@app.post("/telegram", tags=["telegram"], include_in_schema=False)
async def telegram(request: Request) -> dict:
    """Webhook de Telegram: verifica el secreto, enruta el mensaje y
    responde al usuario. A Telegram siempre se le responde 200."""
    # 1. Verificar el secreto del webhook
    secreto_recibido = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not TELEGRAM_SECRET or secreto_recibido != TELEGRAM_SECRET:
        raise HTTPException(status_code=403, detail="Secreto de webhook inválido.")

    # 2. Parsear el update
    try:
        update = await request.json()
    except Exception:
        logger.warning("/telegram recibió un body que no es JSON válido")
        return {"ok": True}

    mensaje = update.get("message") or {}
    texto = mensaje.get("text")
    chat_id = (mensaje.get("chat") or {}).get("id")

    # 3. Ignorar updates sin texto (fotos, stickers, ediciones, etc.)
    if not texto or chat_id is None:
        logger.info("Update de Telegram ignorado (sin texto): %s", update)
        return {"ok": True}

    # 4. Enrutar y responder al usuario
    try:
        estado = graph.invoke(
            {"mensaje": texto},
            {"configurable": {"thread_id": str(chat_id)}},
        )
        async with httpx.AsyncClient(timeout=30) as cliente:
            respuesta = await cliente.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": estado["respuesta"]},
            )
            respuesta.raise_for_status()
    except Exception:
        logger.exception("Error procesando update de Telegram (chat_id=%s)", chat_id)

    # 5. Responder 200 a Telegram siempre, haya funcionado o no
    return {"ok": True}
