"""Registra el webhook de Telegram apuntando a PUBLIC_URL + /telegram.

Uso (desde la raiz del proyecto):
    .venv\\Scripts\\python.exe scripts/set_webhook.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
SECRET = os.getenv("TELEGRAM_SECRET")
PUBLIC_URL = os.getenv("PUBLIC_URL")

faltan = [
    nombre
    for nombre, valor in [
        ("TELEGRAM_TOKEN", TOKEN),
        ("TELEGRAM_SECRET", SECRET),
        ("PUBLIC_URL", PUBLIC_URL),
    ]
    if not valor
]
if faltan:
    print(f"Faltan variables en .env: {', '.join(faltan)}")
    sys.exit(1)

url = PUBLIC_URL.rstrip("/") + "/telegram"
print(f"Registrando webhook: {url}")

respuesta = httpx.post(
    f"https://api.telegram.org/bot{TOKEN}/setWebhook",
    json={"url": url, "secret_token": SECRET},
    timeout=30,
)
print(respuesta.json())
