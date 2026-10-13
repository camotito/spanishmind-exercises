#!/usr/bin/env python3
"""
Cliente compartido para llamadas a Gemini con imagen + texto (vision), pensado
para extraer el libro escaneado (libro_pipeline/extract_*.py).

Responsabilidades:
  - Llamada a generateContent con imagen inline + prompt de texto.
  - Reintentos con backoff exponencial + jitter en 429/5xx, respetando el
    header Retry-After si el servidor lo manda.
  - Throttle por RPM (configurable, conservador por defecto).
  - Checkpoint en disco: qué páginas/claves ya se procesaron con éxito, para
    poder cortar la ejecución (limite diario, Ctrl-C, corte de cuota) y
    retomarla despues sin repetir trabajo ni gastar cuota de más.

No asume un RPD exacto: como el checkpoint hace idempotente cada llamada,
si un 429 persiste tras agotar reintentos simplemente se detiene con un
mensaje claro y se puede relanzar el script más tarde (mismo comando).
"""
import base64
import json
import os
import random
import sys
import time

import requests

from openai_client import InsufficientQuotaError

DEFAULT_MODEL = "gemini-3.5-flash"
API_URL_TMPL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def strip_code_fence(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        text = text.removeprefix("json").strip()
    return text


class GeminiVisionClient:
    def __init__(
        self,
        checkpoint_path,
        model=DEFAULT_MODEL,
        rpm=8,
        max_retries=6,
    ):
        self.key = os.environ.get("GEMINI_API_KEY")
        if not self.key:
            sys.exit("Falta GEMINI_API_KEY en el entorno")
        self.model = model
        self.api_url = API_URL_TMPL.format(model=model)
        self.min_interval = 60.0 / rpm
        self.max_retries = max_retries
        self.checkpoint_path = checkpoint_path
        self._last_call_ts = 0.0
        self.checkpoint = self._load_checkpoint()

    # ---- checkpoint ----

    def _load_checkpoint(self):
        if os.path.exists(self.checkpoint_path):
            with open(self.checkpoint_path, encoding="utf-8") as f:
                return json.load(f)
        return {"completados": {}, "fallidos": {}}

    def _save_checkpoint(self):
        os.makedirs(os.path.dirname(self.checkpoint_path) or ".", exist_ok=True)
        with open(self.checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(self.checkpoint, f, ensure_ascii=False, indent=2)

    def is_done(self, key):
        return key in self.checkpoint["completados"]

    def mark_done(self, key, meta=None):
        self.checkpoint["completados"][key] = meta or True
        self.checkpoint["fallidos"].pop(key, None)
        self._save_checkpoint()

    def mark_failed(self, key, error):
        self.checkpoint["fallidos"][key] = str(error)
        self._save_checkpoint()

    # ---- llamada ----

    def _throttle(self):
        wait = self.min_interval - (time.monotonic() - self._last_call_ts)
        if wait > 0:
            time.sleep(wait)
        self._last_call_ts = time.monotonic()

    def call(self, image_path, prompt_text):
        """Devuelve el texto de la respuesta (sin fence ```json), o lanza tras agotar reintentos."""
        with open(image_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("ascii")

        mime = "image/jpeg" if image_path.lower().endswith((".jpg", ".jpeg")) else "image/png"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt_text},
                        {"inline_data": {"mime_type": mime, "data": image_b64}},
                    ]
                }
            ],
            "generationConfig": {"responseMimeType": "application/json"},
        }

        for attempt in range(self.max_retries):
            self._throttle()
            resp = requests.post(f"{self.api_url}?key={self.key}", json=payload, timeout=280)

            if resp.status_code == 429 and attempt < self.max_retries - 1:
                retry_after = resp.headers.get("Retry-After")
                if retry_after:
                    wait = float(retry_after)
                else:
                    wait = min(2**attempt * 5, 120) + random.uniform(0, 3)
                print(f"  ⏳ 429 (rate limit) en {os.path.basename(image_path)}, reintentando en {wait:.0f}s...")
                time.sleep(wait)
                continue

            if resp.status_code >= 500 and attempt < self.max_retries - 1:
                wait = min(2**attempt * 5, 60) + random.uniform(0, 3)
                print(f"  ⏳ {resp.status_code} en {os.path.basename(image_path)}, reintentando en {wait:.0f}s...")
                time.sleep(wait)
                continue

            if resp.status_code == 402:
                raise InsufficientQuotaError(
                    "Gemini 402: creditos prepago agotados en la cuenta de facturacion. "
                    "Compra creditos en AI Studio (Billing) y relanza: retoma solo."
                )
            if not resp.ok:
                # sin resp.raise_for_status(): su mensaje incluye la URL con la clave (?key=...)
                raise RuntimeError(f"Gemini HTTP {resp.status_code}: {resp.text[:300]}")
            data = resp.json()
            # los modelos con razonamiento pueden devolver partes "thought": se ignoran
            parts = data["candidates"][0]["content"]["parts"]
            texto = "".join(p.get("text", "") for p in parts if not p.get("thought"))
            return strip_code_fence(texto)

        raise RuntimeError(f"Agotados los reintentos para {image_path} (último status: {resp.status_code})")
