"""Clasificacion y reformateo con LLM."""

from __future__ import annotations

import re
from typing import Any

import requests

from config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_URL,
    ANTHROPIC_VERSION,
    MIN_CHARS_FOR_SMART,
    MODEL_FAST,
    MODEL_SMART,
    REQUEST_TIMEOUT_SECONDS,
)

SYSTEM_PROMPT = """Eres un procesador especializado de material docente universitario.
Recibes fragmentos de texto extraidos de documentos academicos (PDF o PPTX).
Tu unica funcion es clasificar y reformatear ese contenido en Markdown estructurado.

REGLAS ABSOLUTAS:
1. NO inventes ni anadas ningun contenido que no este en el fragmento recibido.
2. NO corrijas errores tecnicos del original - transcribelos tal cual.
3. NO parafrasees el contenido tecnico. Usa las mismas palabras, terminos y notacion.
4. NO omitas informacion por parecer redundante o poco importante.
5. Si un fragmento es ambiguo, clasificalo como "mixto".
6. Las ecuaciones van en formato LaTeX entre $$ ... $$ (bloque) o $ ... $ (inline).
7. El texto ilegible o corrupto se marca exactamente como: [TEXTO_ILEGIBLE]
8. Las figuras o imagenes se marcan exactamente como: [FIGURA: descripcion si existe]
9. Detecta el idioma del fragmento (espanol o ingles) y mantenlo en el output. Los marcadores tecnicos [FIGURA], [TEXTO_ILEGIBLE] son siempre en espanol.

FORMATO DE SECCIONES EN EL OUTPUT:
El campo "contenido_markdown" debe usar estos nombres de seccion fijos segun el idioma detectado.
NUNCA uses nombres de seccion distintos a los de esta tabla.
NUNCA crees una seccion si no hay contenido de ese tipo en el fragmento.

Tipo        | Seccion ES                  | Seccion EN
------------|-----------------------------|-----------------------
teoria      | ## Contenido teorico        | ## Theory
ejemplo_res | ## Ejemplos resueltos       | ## Solved examples
ejercicio   | ## Ejercicios propuestos    | ## Practice problems
tabla       | ## Tablas de referencia     | ## Reference tables
procedimien | ## Procedimientos           | ## Procedures
resumen     | ## Resumen                  | ## Summary
mixto       | ## Contenido                | ## Content

Reglas adicionales de formato:
- Un solo # H1 por chunk si hay titulo detectado, ninguno si no lo hay.
- Subsecciones con ### H3 si el bloque tiene titulo, parrafo directo si no.
- Ecuaciones siempre en LaTeX: $$ ... $$ para bloque, $ ... $ para inline.
- Figuras siempre como: [FIGURA: descripcion si existe]
- Texto ilegible siempre como: [TEXTO_ILEGIBLE]
- Resultados de ejercicios en blockquote: > 💡 *Resultado:* valor
- Separadores --- entre secciones ## H2, nunca dentro de ellas.
- Los marcadores [FIGURA] y [TEXTO_ILEGIBLE] son SIEMPRE en espanol,
  independientemente del idioma del documento.

CLASIFICACION DE TIPOS:
- "teoria": definiciones, principios, descripciones, ecuaciones sin enunciado de problema
- "ejemplo_resuelto": enunciado + desarrollo + resultado
- "ejercicio_propuesto": enunciado sin desarrollo completo (puede tener resultado numerico final)
- "tabla": datos tabulados
- "procedimiento": pasos secuenciales
- "resumen": recapitulacion explicita de seccion
- "mixto": combinacion no separable de los anteriores

FORMATO DE SALIDA:
Responde usando exactamente estos delimitadores, sin texto adicional:

<TIPO>clasificacion aqui</TIPO>
<TITULO>titulo detectado o null</TITULO>
<IDIOMA>es o en</IDIOMA>
<MARKDOWN>
contenido markdown aqui, puede tener saltos de linea y cualquier caracter
</MARKDOWN>
"""

VALID_TYPES = {
    "teoria",
    "ejemplo_resuelto",
    "ejercicio_propuesto",
    "tabla",
    "procedimiento",
    "resumen",
    "mixto",
}
VALID_LANGUAGES = {"es", "en"}

MATH_SYMBOLS = set("∫∑∂∇×·√ΔΩαβγδεζηθλμνξπρστφχψω=<>≤≥±")


def _parse_delimited_response(raw: str) -> dict:
    def extract_tag(tag: str) -> str | None:
        # Busca contenido entre <TAG> y </TAG>, tolerando espacios y saltos
        match = re.search(
            rf"<{tag}>\s*(.*?)\s*</{tag}>",
            raw,
            re.DOTALL | re.IGNORECASE,
        )
        return match.group(1).strip() if match else None

    def extract_markdown(raw_text: str) -> str:
        # Intenta con tag de cierre normal
        match = re.search(
            r"<MARKDOWN>\s*(.*?)\s*</MARKDOWN>",
            raw_text,
            re.DOTALL | re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()
        # Fallback: toma todo lo que viene después de <MARKDOWN>
        match = re.search(r"<MARKDOWN>\s*(.*)", raw_text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return ""

    tipo = extract_tag("TIPO") or "mixto"
    titulo = extract_tag("TITULO")
    if titulo and titulo.lower() in ("null", "none", ""):
        titulo = None
    idioma = extract_tag("IDIOMA") or "es"
    if idioma not in ("es", "en"):
        idioma = "es"
    markdown = extract_markdown(raw)

    return {
        "tipo": tipo,
        "titulo_detectado": titulo,
        "idioma": idioma,
        "contenido_markdown": markdown,
    }


def select_model(chunk_text: str) -> str:
    """Selecciona modelo segun densidad matematica del chunk."""
    if not chunk_text:
        return MODEL_FAST
    if len(chunk_text) < MIN_CHARS_FOR_SMART:
        return MODEL_FAST
    symbol_density = sum(1 for c in chunk_text if c in MATH_SYMBOLS) / len(chunk_text)
    has_equation_patterns = any(p in chunk_text for p in ["d/dt", "d²", "∫", "Σ", "="])
    if symbol_density > 0.02 or has_equation_patterns:
        return MODEL_SMART
    return MODEL_FAST


def _call_anthropic(chunk_text: str) -> dict[str, Any]:
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("Falta ANTHROPIC_API_KEY en .env")

    model = select_model(chunk_text)
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": model,
        "max_tokens": 2048,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": chunk_text}],
    }

    last_raw = ""
    for attempt in range(3):
        response = requests.post(
            ANTHROPIC_URL,
            headers=headers,
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"Anthropic error {response.status_code}: {response.text}")
        raw = str(response.json()["content"][0]["text"])
        last_raw = raw
        parsed = _parse_delimited_response(raw)
        contenido = str(parsed.get("contenido_markdown", "")).strip()

        m_tipo = re.search(
            r"<TIPO>\s*(.*?)\s*</TIPO>",
            raw,
            re.DOTALL | re.IGNORECASE,
        )
        tipo_tag_presente = m_tipo is not None

        if contenido:
            tipo = str(parsed.get("tipo", "mixto")).strip()
            if tipo not in VALID_TYPES:
                tipo = "mixto"
            idioma = str(parsed.get("idioma", "es")).strip().lower() or "es"
            if idioma not in VALID_LANGUAGES:
                idioma = "es"
            return {
                "tipo": tipo,
                "titulo_detectado": parsed.get("titulo_detectado"),
                "idioma": idioma,
                "contenido_markdown": contenido,
            }

        debe_reintentar = (not contenido) or (not tipo_tag_presente)
        if debe_reintentar and attempt < 2:
            razon = "markdown vacio"
            if not tipo_tag_presente:
                razon = "markdown vacio o TIPO ausente"
            print(f"Advertencia: {razon}, reintentando intento {attempt + 1}")
            continue
        break
    raise RuntimeError(
        f"contenido_markdown vacio tras reintentos. Ultima respuesta: {last_raw}"
    )


def classify_and_format(fragment: str) -> dict[str, Any]:
    """Clasifica y formatea un fragmento devolviendo un dict validado."""
    data = _call_anthropic(fragment.strip())

    tipo = str(data.get("tipo", "mixto")).strip()
    if tipo not in VALID_TYPES:
        tipo = "mixto"

    titulo = data.get("titulo_detectado")
    if titulo is not None and not isinstance(titulo, str):
        titulo = None

    idioma = str(data.get("idioma", "es")).strip().lower() or "es"
    if idioma not in VALID_LANGUAGES:
        idioma = "es"

    contenido = str(data.get("contenido_markdown", "")).strip()
    if not contenido:
        raise RuntimeError("contenido_markdown vacio")

    return {
        "tipo": tipo,
        "titulo_detectado": titulo,
        "idioma": idioma,
        "contenido_markdown": contenido,
    }
