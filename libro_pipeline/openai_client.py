#!/usr/bin/env python3
"""
Cliente compartido para llamadas a OpenAI (Responses API) con imagen + texto,
misma interfaz que gemini_client.GeminiVisionClient (checkpoint, reintentos,
call(image_path, prompt_text, schema=None) -> texto) para poder usarlos de
forma intercambiable en el pipeline.

Se usa sobre todo para la doble verificacion del solucionario: extraer la
misma pagina con Gemini y con OpenAI y comparar, en vez de fiarnos de un
solo modelo en texto denso donde ambos cometen errores de contenido que la
validacion por conteo de huecos no detecta.
"""
import base64
import json
import os
import random
import sys
import time

import requests

DEFAULT_MODEL = "gpt-5.6-sol"
API_URL = "https://api.openai.com/v1/responses"


def strip_code_fence(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        text = text.removeprefix("json").strip()
    return text


class InsufficientQuotaError(RuntimeError):
    """Saldo de credito agotado -- inutil reintentar, hay que parar el pipeline entero
    hasta que se añada saldo (a diferencia de un rate_limit_exceeded normal, que sí
    se resuelve solo esperando)."""


class OpenAIVisionClient:
    def __init__(
        self,
        checkpoint_path,
        model=DEFAULT_MODEL,
        rpm=20,
        max_retries=6,
    ):
        self.key = os.environ.get("OPENAI_API_KEY")
        if not self.key:
            sys.exit("Falta OPENAI_API_KEY en el entorno")
        self.model = model
        self.min_interval = 60.0 / rpm
        self.max_retries = max_retries
        self.checkpoint_path = checkpoint_path
        self._last_call_ts = 0.0
        self.checkpoint = self._load_checkpoint()

    # ---- checkpoint (mismo formato que GeminiVisionClient) ----

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

    def call(self, image_path, prompt_text, schema=None):
        """Devuelve el texto de la respuesta (JSON si se pasa schema), o lanza tras agotar reintentos."""
        with open(image_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("ascii")

        payload = {
            "model": self.model,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt_text},
                        {"type": "input_image", "image_url": f"data:image/png;base64,{image_b64}"},
                    ],
                }
            ],
        }
        if schema is not None:
            payload["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": "Extraccion",
                    "schema": schema,
                    "strict": True,
                }
            }

        for attempt in range(self.max_retries):
            self._throttle()
            resp = requests.post(
                API_URL,
                headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
                json=payload,
                timeout=120,
            )

            if resp.status_code == 429:
                # OpenAI usa 429 tanto para "vas demasiado rapido" (rate_limit_exceeded,
                # reintentable) como para "no tienes saldo" (insufficient_quota, inutil
                # reintentar -- fallar rapido con mensaje claro en vez de agotar
                # reintentos con esperas de hasta 120s que nunca se van a resolver solas).
                try:
                    error_type = resp.json().get("error", {}).get("type", "")
                except ValueError:
                    error_type = ""
                if error_type == "insufficient_quota":
                    raise InsufficientQuotaError(
                        "OpenAI: saldo de credito agotado (insufficient_quota) -- "
                        "añade saldo o activa auto-recharge en platform.openai.com/settings/organization/billing "
                        "antes de reintentar. No tiene sentido esperar, esto no se resuelve solo."
                    )
                if attempt < self.max_retries - 1:
                    retry_after = resp.headers.get("Retry-After")
                    wait = float(retry_after) if retry_after else min(2**attempt * 5, 120) + random.uniform(0, 3)
                    print(f"  ⏳ 429 (rate limit) en {os.path.basename(image_path)}, reintentando en {wait:.0f}s...")
                    time.sleep(wait)
                    continue

            if resp.status_code >= 500 and attempt < self.max_retries - 1:
                wait = min(2**attempt * 5, 60) + random.uniform(0, 3)
                print(f"  ⏳ {resp.status_code} en {os.path.basename(image_path)}, reintentando en {wait:.0f}s...")
                time.sleep(wait)
                continue

            resp.raise_for_status()
            data = resp.json()
            for item in data.get("output", []):
                if item.get("type") == "message":
                    for block in item.get("content", []):
                        if block.get("type") in ("output_text", "text"):
                            return strip_code_fence(block["text"])
            raise RuntimeError(f"Sin texto de salida en la respuesta: {json.dumps(data)[:500]}")

        raise RuntimeError(f"Agotados los reintentos para {image_path} (último status: {resp.status_code})")
