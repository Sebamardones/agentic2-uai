"""Muestra el estado del webhook de Telegram (getWebhookInfo).

Uso (desde la raiz del proyecto):
    .venv\\Scripts\\python.exe scripts/webhook_info.py
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    print("Falta TELEGRAM_TOKEN en .env")
    sys.exit(1)

respuesta = httpx.get(
    f"https://api.telegram.org/bot{TOKEN}/getWebhookInfo", timeout=30
)
info = respuesta.json()

print(json.dumps(info, indent=2, ensure_ascii=False))

if info.get("ok") and info.get("result"):
    r = info["result"]
    print(f"\nurl: {r.get('url')}")
    print(f"pending_update_count: {r.get('pending_update_count')}")
    if r.get("last_error_message"):
        print(f"ULTIMO ERROR: {r['last_error_message']} ({r.get('last_error_date')})")
