"""Pruebas de la API (no llaman al modelo)."""

import importlib

import pytest
from fastapi.testclient import TestClient

app_module = importlib.import_module("api.app")

client = TestClient(app_module.app)

API_KEY_PRUEBA = "clave-api-de-prueba"
API_KEY_HEADER = {"X-API-Key": API_KEY_PRUEBA}
SECRETO_HEADER = {
    "X-Telegram-Bot-Api-Secret-Token": app_module.TELEGRAM_SECRET,
}


@pytest.fixture(autouse=True)
def configurar_api_key(monkeypatch):
    monkeypatch.setattr(app_module, "API_KEY", API_KEY_PRUEBA)


def test_health():
    respuesta = client.get("/health")
    assert respuesta.status_code == 200
    assert respuesta.json()["ok"] is True
    assert respuesta.json()["memoria"] in {"ram", "postgres"}


def test_chat_falta_texto_422():
    respuesta = client.post("/chat", headers=API_KEY_HEADER, json={"user_id": "u1"})
    assert respuesta.status_code == 422


def test_chat_sin_clave_401():
    respuesta = client.post(
        "/chat",
        json={"user_id": "u1", "texto": "hola"},
    )
    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": "Clave de API ausente o inválida."}


def test_chat_con_clave_200(monkeypatch):
    monkeypatch.setattr(
        app_module.graph,
        "invoke",
        lambda *args, **kwargs: {
            "ruta": "generica",
            "motivo": "Es un saludo.",
            "respuesta": "Hola.",
        },
    )

    respuesta = client.post(
        "/chat",
        headers=API_KEY_HEADER,
        json={"user_id": "u1", "texto": "hola"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ruta": "generica",
        "motivo": "Es un saludo.",
        "respuesta": "Hola.",
    }


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
