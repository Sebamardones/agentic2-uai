"""Pruebas de la API (no llaman al modelo)."""

from fastapi.testclient import TestClient

from api.app import TELEGRAM_SECRET, app

client = TestClient(app)

SECRETO_HEADER = {"X-Telegram-Bot-Api-Secret-Token": TELEGRAM_SECRET}


def test_health():
    respuesta = client.get("/health")
    assert respuesta.status_code == 200
    assert respuesta.json()["ok"] is True


def test_chat_falta_texto_422():
    respuesta = client.post("/chat", json={"user_id": "u1"})
    assert respuesta.status_code == 422


def test_telegram_sin_secreto_403():
    respuesta = client.post(
        "/telegram",
        json={"message": {"chat": {"id": 1}, "text": "hola"}},
    )
    assert respuesta.status_code == 403


def test_telegram_update_sin_texto_200():
    respuesta = client.post(
        "/telegram",
        headers=SECRETO_HEADER,
        json={"message": {"chat": {"id": 1}, "photo": []}},
    )
    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True}
