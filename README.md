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

El bot se conecta a la API por **webhook** (sin librerías de bot, solo `httpx`):
Telegram hace `POST` a `/telegram` con cada mensaje; la API verifica el
secreto, enruta el texto con el grafo (con `thread_id = chat_id`, así cada
chat tiene su propia memoria) y responde al usuario con `sendMessage`.

### Pasos finales, en orden

**0. Crear el bot.** En Telegram, habla con **@BotFather**: `/newbot`, dale
nombre y username, y copia el token que te devuelve a `TELEGRAM_TOKEN` en tu
`.env`. Elige también un `TELEGRAM_SECRET` (cualquier texto largo y aleatorio)
y ponlo en `.env`. Nunca subas estos valores al repo.

**1. Configurar las variables en Heroku:**

```bash
heroku config:set TELEGRAM_TOKEN="el-token-que-te-dio-BotFather"
heroku config:set TELEGRAM_SECRET="tu-secreto-largo-y-aleatorio"
heroku config:set PUBLIC_URL="https://TU-APP.herokuapp.com"
```

**2. Subir los cambios** a GitHub y a Heroku:

```bash
git add .
git commit -m "telegram webhook"
git push origin main
git push heroku main
```

**3. Registrar el webhook y confirmar.** Con `PUBLIC_URL` de Heroku en el
`.env` (y el token y el secreto):

```bash
.venv\Scripts\python.exe scripts/set_webhook.py     # registra url=PUBLIC_URL/telegram + secret_token
.venv\Scripts\python.exe scripts/webhook_info.py    # confirma url y muestra errores pendientes
```

**4. Probar.** Escribe al bot los mensajes de prueba del router (p. ej.
"¿tienen la polera azul en talla M?", "mi pedido 4521 llegó roto", "hola", ...).
Verifica en los logs que cada mensaje enrutó a la ruta correcta:

```bash
heroku logs --tail
```

**5. Si no responde, revisa en este orden:**

- `webhook_info.py` muestra `url` apuntando a `https://.../telegram` (debe ser
  **https**, no http; Heroku lo da así).
- El `TELEGRAM_SECRET` es **idéntico** en el `.env`, en `heroku config` y en
  lo que se mandó a `setWebhook` (si lo cambiaste después, vuelve a correr
  `set_webhook.py`).
- El `TELEGRAM_TOKEN` es el del bot correcto (sin espacios ni el prefijo
  `bot`).
- La app está arriba: `curl.exe https://TU-APP.herokuapp.com/health`.
- Los logs: `heroku logs --tail` muestra el 403 (secreto) o el error del
  modelo (502 interno) si los hay.

### Probar en local antes de desplegar (opcional)

Expón tu API local con un túnel y úsalo como `PUBLIC_URL`:

```bash
cloudflared tunnel --url http://localhost:8000
```

Copia la URL `https://...trycloudflare.com` que imprime a `PUBLIC_URL` en el
`.env` y corre `scripts/set_webhook.py`: Telegram llegará a tu máquina local.
Para volver a Heroku, repite el paso 3 con la URL de Heroku.

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
