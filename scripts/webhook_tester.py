"""Aplicacion web local para probar el webhook de n8n.

Ejecutar desde la raiz:
    python scripts/webhook_tester.py
"""

import os
from typing import Literal

import httpx
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

load_dotenv()

WEBHOOK_URL = os.getenv(
    "N8N_WEBHOOK_URL",
    "https://sebamardones.app.n8n.cloud/webhook/agente-web-local",
)
WEBHOOK_API_KEY = os.getenv("N8N_WEBHOOK_API_KEY", os.getenv("API_KEY", ""))

app = FastAPI(title="Webhook Lab", docs_url=None, redoc_url=None)


class SolicitudWebhook(BaseModel):
    tipo: Literal["texto", "voz", "gif"]
    user_id: str = Field(min_length=1, max_length=100)
    texto: str = ""
    archivo_base64: str = ""
    mime_type: str = ""
    nombre_archivo: str = ""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def inicio() -> str:
    return PAGINA


@app.post("/api/enviar", include_in_schema=False)
async def enviar(solicitud: SolicitudWebhook) -> JSONResponse:
    if not WEBHOOK_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Falta N8N_WEBHOOK_API_KEY o API_KEY en el entorno local.",
        )
    if solicitud.tipo == "texto" and not solicitud.texto.strip():
        raise HTTPException(status_code=422, detail="Escribe un mensaje.")
    if solicitud.tipo in {"voz", "gif"} and not solicitud.archivo_base64:
        raise HTTPException(status_code=422, detail="Selecciona un archivo.")

    payload = {
        "tipo": solicitud.tipo,
        "user_id": solicitud.user_id,
        "texto": solicitud.texto.strip(),
        "audio_base64": (
            solicitud.archivo_base64 if solicitud.tipo == "voz" else ""
        ),
        "mime_type": solicitud.mime_type,
        "filename": solicitud.nombre_archivo,
    }

    try:
        async with httpx.AsyncClient(timeout=45) as cliente:
            respuesta = await cliente.post(
                WEBHOOK_URL,
                headers={"X-API-Key": WEBHOOK_API_KEY},
                json=payload,
            )
    except httpx.RequestError as error:
        raise HTTPException(
            status_code=502,
            detail=f"No se pudo conectar con n8n: {error}",
        ) from error

    try:
        contenido = respuesta.json()
    except ValueError:
        contenido = {"ok": False, "error": respuesta.text or "Respuesta vacia."}

    return JSONResponse(status_code=respuesta.status_code, content=contenido)


PAGINA = r"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Webhook Lab</title>
  <style>
    :root {
      color-scheme: dark;
      --ink: #eef6ec;
      --muted: #91a092;
      --panel: #111713;
      --line: #293329;
      --acid: #b8ff5a;
      --orange: #ff875a;
      --paper: #090d0a;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      background:
        linear-gradient(rgba(184,255,90,.035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(184,255,90,.035) 1px, transparent 1px),
        var(--paper);
      background-size: 28px 28px;
      font-family: Consolas, "Courier New", monospace;
    }
    body::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background: radial-gradient(circle at 75% 10%, rgba(184,255,90,.1), transparent 32%);
    }
    .shell { width: min(1180px, calc(100% - 32px)); margin: 0 auto; padding: 42px 0; }
    header { display: flex; justify-content: space-between; gap: 24px; align-items: end; margin-bottom: 28px; }
    .eyebrow { color: var(--acid); letter-spacing: .18em; font-size: 12px; text-transform: uppercase; }
    h1 { margin: 8px 0 0; font-size: clamp(34px, 6vw, 72px); line-height: .9; letter-spacing: -.07em; }
    .target { max-width: 390px; color: var(--muted); font-size: 12px; text-align: right; overflow-wrap: anywhere; }
    .target::before { content: "LIVE "; color: var(--acid); }
    .grid { display: grid; grid-template-columns: 1.05fr .95fr; gap: 18px; }
    .panel { border: 1px solid var(--line); background: rgba(17,23,19,.94); box-shadow: 8px 8px 0 #050705; }
    .panel-title { display: flex; justify-content: space-between; padding: 14px 16px; border-bottom: 1px solid var(--line); color: var(--muted); font-size: 12px; text-transform: uppercase; }
    form { padding: 18px; }
    label.field { display: block; margin-bottom: 18px; }
    label.field > span { display: block; color: var(--muted); font-size: 11px; margin-bottom: 7px; text-transform: uppercase; }
    input[type="text"], textarea {
      width: 100%; border: 1px solid var(--line); background: #080c09; color: var(--ink);
      padding: 13px 14px; border-radius: 0; outline: none; font: inherit;
    }
    textarea { min-height: 142px; resize: vertical; }
    input:focus, textarea:focus { border-color: var(--acid); box-shadow: 0 0 0 2px rgba(184,255,90,.12); }
    .modes { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 20px; }
    .mode input { position: absolute; opacity: 0; }
    .mode span { display: block; border: 1px solid var(--line); padding: 13px 10px; text-align: center; color: var(--muted); cursor: pointer; }
    .mode input:checked + span { color: #0a0d0a; background: var(--acid); border-color: var(--acid); font-weight: 700; }
    .drop {
      display: none; border: 1px dashed #536153; padding: 26px 14px; text-align: center;
      color: var(--muted); cursor: pointer; margin-bottom: 18px;
    }
    .drop.active { display: block; }
    .drop:hover { border-color: var(--acid); color: var(--ink); }
    .drop strong { display: block; color: var(--ink); margin-bottom: 6px; }
    .file-name { margin-top: 10px; color: var(--orange); font-size: 12px; }
    .actions { display: flex; align-items: center; gap: 14px; }
    button {
      border: 0; background: var(--acid); color: #080b08; padding: 14px 22px;
      font: 700 13px Consolas, monospace; cursor: pointer; text-transform: uppercase;
    }
    button:hover { transform: translate(-2px, -2px); box-shadow: 4px 4px 0 #56782a; }
    button:disabled { opacity: .45; cursor: wait; transform: none; box-shadow: none; }
    #estado { color: var(--muted); font-size: 12px; }
    .console { min-height: 440px; padding: 18px; display: flex; flex-direction: column; }
    .console pre { margin: 0; white-space: pre-wrap; word-break: break-word; font: 13px/1.65 Consolas, monospace; flex: 1; }
    .empty { color: #526052; }
    .status { display: inline-flex; align-items: center; gap: 7px; color: var(--muted); }
    .status::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--acid); box-shadow: 0 0 10px var(--acid); }
    .meta { border-top: 1px solid var(--line); padding-top: 14px; margin-top: 18px; color: var(--muted); font-size: 11px; }
    @media (max-width: 780px) {
      .shell { width: min(100% - 20px, 620px); padding: 24px 0; }
      header { display: block; }
      .target { text-align: left; margin-top: 18px; }
      .grid { grid-template-columns: 1fr; }
      .console { min-height: 300px; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <header>
      <div><div class="eyebrow">n8n integration bench</div><h1>WEBHOOK<br>LAB</h1></div>
      <div class="target">sebamardones.app.n8n.cloud / agente-web-local</div>
    </header>
    <section class="grid">
      <article class="panel">
        <div class="panel-title"><span>01 / entrada</span><span class="status">proxy local</span></div>
        <form id="formulario">
          <label class="field"><span>Identidad de prueba</span><input id="userId" type="text" value="web-local-001" maxlength="100" required></label>
          <div class="modes">
            <label class="mode"><input type="radio" name="tipo" value="texto" checked><span>Texto</span></label>
            <label class="mode"><input type="radio" name="tipo" value="voz"><span>Voz</span></label>
            <label class="mode"><input type="radio" name="tipo" value="gif"><span>GIF</span></label>
          </div>
          <label class="field" id="campoTexto"><span>Mensaje</span><textarea id="texto" placeholder="Escribe algo para el agente...">Hola, ¿qué productos tienen?</textarea></label>
          <label class="drop" id="campoArchivo">
            <input id="archivo" type="file" hidden>
            <strong id="instruccionArchivo">Seleccionar archivo</strong>
            <span>Máximo recomendado: 10 MB</span>
            <div class="file-name" id="nombreArchivo"></div>
          </label>
          <div class="actions"><button id="enviar" type="submit">Ejecutar webhook</button><span id="estado">Listo.</span></div>
        </form>
      </article>
      <article class="panel">
        <div class="panel-title"><span>02 / respuesta</span><span id="codigo">HTTP —</span></div>
        <div class="console"><pre id="salida" class="empty">Esperando una ejecución...</pre><div class="meta" id="duracion">La clave queda en el servidor local y nunca llega al navegador.</div></div>
      </article>
    </section>
  </main>
  <script>
    const form = document.querySelector('#formulario');
    const campoTexto = document.querySelector('#campoTexto');
    const campoArchivo = document.querySelector('#campoArchivo');
    const archivo = document.querySelector('#archivo');
    const salida = document.querySelector('#salida');
    const codigo = document.querySelector('#codigo');
    const estado = document.querySelector('#estado');
    const boton = document.querySelector('#enviar');
    const nombreArchivo = document.querySelector('#nombreArchivo');
    const instruccionArchivo = document.querySelector('#instruccionArchivo');

    function tipoActual() { return document.querySelector('input[name="tipo"]:checked').value; }
    function actualizarModo() {
      const tipo = tipoActual();
      campoTexto.style.display = tipo === 'texto' ? 'block' : 'none';
      campoArchivo.classList.toggle('active', tipo !== 'texto');
      archivo.accept = tipo === 'voz' ? 'audio/*' : 'image/gif';
      instruccionArchivo.textContent = tipo === 'voz' ? 'Seleccionar audio' : 'Seleccionar GIF';
      archivo.value = '';
      nombreArchivo.textContent = '';
    }
    document.querySelectorAll('input[name="tipo"]').forEach(input => input.addEventListener('change', actualizarModo));
    archivo.addEventListener('change', () => { nombreArchivo.textContent = archivo.files[0]?.name || ''; });

    function leerBase64(file) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result).split(',')[1]);
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });
    }

    form.addEventListener('submit', async event => {
      event.preventDefault();
      const inicio = performance.now();
      const tipo = tipoActual();
      const file = archivo.files[0];
      if (tipo !== 'texto' && !file) { estado.textContent = 'Selecciona un archivo.'; return; }
      if (file && file.size > 10 * 1024 * 1024) { estado.textContent = 'El archivo supera 10 MB.'; return; }
      boton.disabled = true;
      estado.textContent = 'Enviando...';
      salida.classList.remove('empty');
      salida.textContent = 'POST /api/enviar\nEsperando respuesta de n8n...';
      try {
        const payload = {
          tipo,
          user_id: document.querySelector('#userId').value,
          texto: document.querySelector('#texto').value,
          archivo_base64: file ? await leerBase64(file) : '',
          mime_type: file?.type || '',
          nombre_archivo: file?.name || ''
        };
        const respuesta = await fetch('/api/enviar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        const contenido = await respuesta.json();
        codigo.textContent = `HTTP ${respuesta.status}`;
        codigo.style.color = respuesta.ok ? 'var(--acid)' : 'var(--orange)';
        salida.textContent = JSON.stringify(contenido, null, 2);
        estado.textContent = respuesta.ok ? 'Completado.' : 'Terminó con error.';
      } catch (error) {
        codigo.textContent = 'ERROR';
        codigo.style.color = 'var(--orange)';
        salida.textContent = String(error);
        estado.textContent = 'No se pudo completar.';
      } finally {
        boton.disabled = false;
        document.querySelector('#duracion').textContent = `Duración: ${Math.round(performance.now() - inicio)} ms`;
      }
    });
  </script>
</body>
</html>"""


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8010)
