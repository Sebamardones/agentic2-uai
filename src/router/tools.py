"""Recursos compartidos del router, incluida su memoria persistente."""

import logging
import os
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, Literal

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

logger = logging.getLogger("router.memory")


@dataclass
class MemoriaRouter:
    checkpointer: BaseCheckpointSaver
    tipo: Literal["ram", "postgres"]


@contextmanager
def abrir_memoria() -> Iterator[MemoriaRouter]:
    """Abre la memoria del router y garantiza el cierre de su pool."""
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        logger.warning("DATABASE_URL no configurada; se usará memoria RAM.")
        yield MemoriaRouter(MemorySaver(), "ram")
        return

    pool = ConnectionPool(
        conninfo=database_url,
        min_size=1,
        max_size=2,
        open=False,
        check=ConnectionPool.check_connection,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
        },
        timeout=5,
        reconnect_timeout=5,
    )
    try:
        pool.open(wait=True, timeout=5)
        checkpointer = PostgresSaver(pool)
        checkpointer.setup()
    except Exception as error:
        pool.close()
        logger.exception(
            "Postgres no está disponible (%s); se usará memoria RAM.", error
        )
        yield MemoriaRouter(MemorySaver(), "ram")
        return

    logger.info("Memoria Postgres lista (pool min=1, max=2).")
    try:
        yield MemoriaRouter(checkpointer, "postgres")
    finally:
        pool.close()
