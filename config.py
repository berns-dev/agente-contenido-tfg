"""Configuracion central para Agente_contenido."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
MODEL_FAST = os.getenv("MODEL_FAST", "claude-haiku-4-5-20251001")
MODEL_SMART = os.getenv("MODEL_SMART", "claude-sonnet-4-5")

CHUNK_TARGET_TOKENS = int(os.getenv("CHUNK_TARGET_TOKENS", "1500"))
CHUNK_CHAR_RATIO = int(os.getenv("CHUNK_CHAR_RATIO", "4"))
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "120"))
MAX_WORKERS = max(1, int(os.getenv("MAX_WORKERS", "5")))
MIN_CHARS_FOR_SMART = int(os.getenv("MIN_CHARS_FOR_SMART", "200"))
