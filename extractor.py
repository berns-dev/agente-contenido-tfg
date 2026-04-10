"""Extraccion de texto desde PDF/PPTX."""

from __future__ import annotations

import re
from pathlib import Path

from cleaner import clean_extracted_text


_CONSONANT_RUN_RE = re.compile(r"(?i)[bcdfghjklmnñpqrstvwxyz]{5,}")
_KNOWN_WORDS = {
    "de",
    "del",
    "la",
    "el",
    "tema",
    "chapter",
    "section",
    "slide",
    "content",
    "engineering",
    "machine",
    "elements",
}


def _is_mirrored_text(line: str) -> bool:
    """
    Detecta texto extraído en espejo (rotado 180°).
    Heurística: una línea es texto en espejo si al invertirla
    forma palabras reales en español o inglés más que el original.
    Señales simples: secuencias de consonantes sin vocales >4 chars,
    o palabras conocidas al revertir.
    """
    stripped = line.strip()
    if len(stripped) < 4:
        return False
    reversed_line = stripped[::-1]
    vowels = set("aeiouáéíóúAEIOUÁÉÍÓÚ")
    original_vowels = sum(1 for c in stripped if c in vowels)
    reversed_vowels = sum(1 for c in reversed_line if c in vowels)
    if len(stripped) > 0:
        ratio = original_vowels / len(stripped)
        if ratio < 0.1 and reversed_vowels > original_vowels:
            return True

    original_tokens = [t.lower() for t in stripped.split()]
    reversed_tokens = [t.lower() for t in reversed_line.split()]
    original_known = sum(1 for t in original_tokens if t in _KNOWN_WORDS)
    reversed_known = sum(1 for t in reversed_tokens if t in _KNOWN_WORDS)
    if reversed_known > original_known and reversed_known > 0:
        return True

    if _CONSONANT_RUN_RE.search(stripped):
        rev_has_consonant_run = _CONSONANT_RUN_RE.search(reversed_line) is not None
        if not rev_has_consonant_run:
            return True
    return False


def _extract_pdf(path: Path) -> str:
    import pdfplumber

    parts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for idx, page in enumerate(pdf.pages, start=1):
            try:
                texto_pagina = page.extract_text() or ""
                print(f"[EXTRACTOR] Página {idx}: {len(texto_pagina)} chars extraídos")
                print(f"[EXTRACTOR] Primeros 200 chars: {repr(texto_pagina[:200])}")
                filtered_lines = [
                    ln for ln in texto_pagina.split("\n") if not _is_mirrored_text(ln)
                ]
                text = clean_extracted_text("\n".join(filtered_lines), path.name).strip()
                if text:
                    parts.append(f"[PAGINA {idx}]\n{text}")
                else:
                    parts.append(f"[PAGINA {idx}]\n[TEXTO_ILEGIBLE]")
            except Exception:
                parts.append(f"[PAGINA {idx}]\n[TEXTO_ILEGIBLE]")
    return "\n\n".join(parts).strip()


def _extract_pptx(path: Path) -> str:
    from pptx import Presentation

    prs = Presentation(str(path))
    parts: list[str] = []
    for idx, slide in enumerate(prs.slides, start=1):
        try:
            slide_lines: list[str] = []
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text:
                    content = str(shape.text).strip()
                    if content:
                        slide_lines.append(content)
            if slide_lines:
                slide_raw_text = "\n".join(slide_lines)
                print(f"[EXTRACTOR] Página {idx}: {len(slide_raw_text)} chars extraídos")
                print(f"[EXTRACTOR] Primeros 200 chars: {repr(slide_raw_text[:200])}")
                filtered_lines = [
                    ln for ln in slide_raw_text.split("\n") if not _is_mirrored_text(ln)
                ]
                slide_text = clean_extracted_text("\n".join(filtered_lines), path.name).strip()
                if slide_text:
                    parts.append(f"[SLIDE {idx}]\n{slide_text}")
                else:
                    parts.append(f"[SLIDE {idx}]\n[TEXTO_ILEGIBLE]")
            else:
                parts.append(f"[SLIDE {idx}]\n[TEXTO_ILEGIBLE]")
        except Exception:
            parts.append(f"[SLIDE {idx}]\n[TEXTO_ILEGIBLE]")
    return "\n\n".join(parts).strip()


def extract_text(file_path: str) -> str:
    """Extrae texto de un PDF o PPTX."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo: {file_path}")

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf(path)
    if suffix == ".pptx":
        return _extract_pptx(path)

    raise ValueError("Formato no soportado. Usa PDF o PPTX.")
