# Ecommerce Router API

Chat de ecommerce con un agente **router** (LangGraph + Gemini): analiza cada
mensaje del cliente y lo deriva a uno de tres destinos:

| Ruta | Cuándo |
|------|--------|
| `preventa` | Intención de compra: productos, precios, tallas, stock, promociones, formas de pago |
| `postventa` | Quejas, seguimiento de pedidos, devoluciones, cambios, garantías, producto dañado |
| `generica` | Temas ajenos a la tienda (saludos, clima, chistes, preguntas generales) |

Los agentes destino son cascarones; lo importante es el enrutado. Expone una
API FastAPI (`api/app.py`) lista para desplegar en Heroku y recibir webhooks
de Telegram.

## Requisitos

- Python 3.12
- Una `GOOGLE_API_KEY` de [Google AI Studio](https://aistudio.google.com/)

## Setup (primera vez)

```bash
# 1. Entorno virtual
python -m venv .venv

# 2. Dependencias
.venv\Scripts\pip install -r requirements.txt

# 3. Variables de entorno
copy .env.example .env
#    y edita .env con tu GOOGLE_API_KEY
```

## Correr el router en local

Desde la raíz del proyecto:

```bash
# Un mensaje (solo respuesta)
.venv\Scripts\python.exe main.py router "¿tienen la polera azul en talla M?"

# Con traza: nodos por los que pasó + motivo del router
.venv\Scripts\python.exe main.py router "mi pedido 4521 llegó roto" --saltos

# Diagrama Mermaid del grafo (sin ejecutar)
.venv\Scripts\python.exe main.py router --diagrama
```

## Levantar la API

```bash
.venv\Scripts\python.exe -m uvicorn api.app:app --reload --port 8000
```

- Swagger UI (probar todo desde el navegador): http://localhost:8000/docs
- Health check: `curl.exe http://localhost:8000/health`

Ejemplo de `/chat`:

```bash
curl.exe -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d "{\"user_id\": \"user-123\", \"texto\": \"¿tienen la polera azul en talla M?\"}"
```

Respuesta:

```json
{
  "ruta": "preventa",
  "motivo": "El cliente pregunta por la disponibilidad de un producto antes de comprar.",
  "respuesta": "Soy el agente de preventa. Recibí: ¿tienen la polera azul en talla M?. Pronto podré ayudarte con productos y compras."
}
```

También puedes probar con la colección Bruno en `bruno/` (entornos `local` y
`heroku` incluidos).

## Correr las pruebas

```bash
# pytest: unitarias + enrutado real (exige al menos 13 de 15 aciertos)
.venv\Scripts\python.exe -m pytest tests/ -v

# Tabla de evaluación con los 15 casos (mensaje, esperado, obtenido, motivo)
.venv\Scripts\python.exe -X utf8 scripts/test_router.py
```

Los casos de prueba viven en `tests/casos_router.json`.

## Desplegar en Heroku

El repo ya trae `Procfile`, `.python-version` (3.12) y `requirements.txt`.

```bash
# 1. Login y crear la app
heroku login
heroku create NOMBRE-DE-TU-APP

# 2. Configurar variables de entorno (NUNCA en el código)
heroku config:set GOOGLE_API_KEY="tu-clave" MODELO="gemini-3.5-flash-lite"
heroku config:set TELEGRAM_SECRET="un-secreto-largo-y-aleatorio"
heroku config:set PUBLIC_URL="https://NOMBRE-DE-TU-APP.herokuapp.com"

# 3. Desplegar
git push heroku main

# 4. Verificar
heroku open
curl.exe https://NOMBRE-DE-TU-APP.herokuapp.com/health
```

## Conectar Telegram

1. En Telegram, habla con **@BotFather** y crea el bot:
   `/newbot` → te devuelve el `TELEGRAM_TOKEN`.
2. Pon el token y el secreto en Heroku (en local, en `.env`):

```bash
heroku config:set TELEGRAM_TOKEN="el-token-que-te-dio-BotFather"
```

3. Una vez desplegada la app con `PUBLIC_URL` configurada, registra el webhook
   (Telegram mandará cada mensaje a `POST /telegram` con el header
   `X-Telegram-Bot-Api-Secret-Token`):

```bash
curl.exe "https://api.telegram.org/bot%TELEGRAM_TOKEN%/setWebhook" -d "url=https://NOMBRE-DE-TU-APP.herokuapp.com/telegram" -d "secret_token=%TELEGRAM_SECRET%"
```

4. Comprueba que quedó activo:

```bash
curl.exe "https://api.telegram.org/bot%TELEGRAM_TOKEN%/getWebhookInfo"
```

> El procesamiento completo del webhook (verificar `TELEGRAM_SECRET` y
> responder al usuario) se implementa en el paso 5; `/telegram` ya recibe
> cualquier JSON y responde `{"ok": true}`.

## Estructura

```
├── main.py                 # CLI: python main.py router "mensaje" [--saltos|--diagrama]
├── api/app.py              # API FastAPI (uvicorn api.app:app --reload --port 8000)
├── src/router/             # graph.py, prompts.py, tools.py
├── tests/                  # pytest + casos_router.json
├── scripts/test_router.py  # evaluación del router con tabla
├── bruno/                  # colección Bruno (entornos local y heroku)
├── Procfile                # web: uvicorn api.app:app --host 0.0.0.0 --port $PORT
└── requirements.txt
```
