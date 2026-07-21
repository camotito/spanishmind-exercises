#!/usr/bin/env python3
"""
Seleccion de proveedor de vision (gemini|openai), compartida por los tres
scripts de extraccion (extract_toc.py, extract_ejercicios.py,
extract_soluciones.py).

Decision (2026-07-15): en las 5 discrepancias verificadas contra el libro
fisico (unidades 27, 38 y 44), OpenAI (gpt-5.6-sol) acerto las 5 y Gemini
(3.1 Flash Lite) fallo las 5 -- por eso "openai" es el default en todo el
pipeline. gemini_client.py se mantiene disponible via --provider gemini
por si hiciera falta contrastar de nuevo en el futuro.
"""
DEFAULT_PROVIDER = "openai"


def build_client(provider, checkpoint_path, model=None):
    if provider == "gemini":
        from gemini_client import GeminiVisionClient, DEFAULT_MODEL

        return GeminiVisionClient(checkpoint_path=checkpoint_path, model=model or DEFAULT_MODEL)
    elif provider == "openai":
        from openai_client import OpenAIVisionClient, DEFAULT_MODEL

        return OpenAIVisionClient(checkpoint_path=checkpoint_path, model=model or DEFAULT_MODEL)
    raise SystemExit(f"--provider desconocido: {provider!r} (usa 'gemini' u 'openai')")


def call_client(client, provider, path, prompt, schema=None):
    """OpenAIVisionClient.call() acepta schema para output estructurado;
    GeminiVisionClient.call() no lo necesita (siempre se le pide JSON en el
    propio prompt)."""
    if provider == "openai":
        return client.call(path, prompt, schema=schema)
    return client.call(path, prompt)
