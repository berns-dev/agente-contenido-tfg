"""Limpieza determinista de texto extraido desde PDF/PPTX."""

from __future__ import annotations

import re
from pathlib import Path

_BOUNDARY_RE = re.compile(r"(?=^\[(?:PAGINA|SLIDE)\s+\d+\])", re.MULTILINE)
_PAGE_NUMBER_RE = re.compile(r"^\s*\d+\s*$")
_FILLER_RE = re.compile(r"^\s*[-–—=_\.·•]{3,}\s*$")
_URL_ONLY_RE = re.compile(r"^\s*https?://\S+\s*$", flags=re.IGNORECASE)
_SLIDE_META_RE = re.compile(r"^\s*(?:Slide|Diapositiva)\s+\d+\s*$", flags=re.IGNORECASE)
_MARKER_RE = re.compile(r"^\s*\[(?:PAGINA|SLIDE)\s+\d+\]\s*$")
_UNIT_RE = re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:%|[kMGT]?W|[kMGT]?Pa|bar|psi|kg|g|mg|m|cm|mm|km|s|min|h|Hz|N|J|V|A|K|C)\b", re.IGNORECASE)
_MULTISPACE_RE = re.compile(r"(\S)[ \t]{2,}(\S)")
_MULTINEWLINES_RE = re.compile(r"\n{3,}")
_EQ_EXPR_RE = re.compile(r"=\s*\S")
_DIGIT_LETTER_RE = re.compile(r"(?i)(?:\d+\s*[a-záéíóúñ]|[a-záéíóúñ]+\s*\d+)")
_WORD_RE = re.compile(r"[A-Za-zÀ-ÿ0-9]+")


def _is_technical_line(line: str) -> bool:
    if "\t" in line or "|" in line:
        return True
    if "$" in line:
        return True
    lowered = line.lower()
    if "\\frac" in lowered or "\\int" in lowered or "\\sum" in lowered:
        return True
    if _EQ_EXPR_RE.search(line):
        return True
    if _UNIT_RE.search(line):
        return True
    return False


def _split_sections(clean: str) -> list[str]:
    if re.search(r"^\[(?:PAGINA|SLIDE)\s+\d+\]", clean, flags=re.MULTILINE):
        return [s.strip() for s in _BOUNDARY_RE.split(clean) if s.strip()]
    return [clean]


def _should_preserve_from_frequency(line: str) -> bool:
    if _DIGIT_LETTER_RE.search(line):
        return True
    words = {w.lower() for w in _WORD_RE.findall(line)}
    if len(words) > 3:
        return True
    if any(ch in line for ch in (":", ",", ";", "(", ")")):
        return True
    return False


def _compute_structural_noise_lines(sections: list[str], filename: str = "") -> set[str]:
    total = len(sections)
    if total == 0:
        return set()
    stem = Path(filename).stem.strip().lower() if filename else ""
    counts: dict[str, int] = {}
    for section in sections:
        seen_in_section: set[str] = set()
        for raw_line in section.split("\n"):
            line = raw_line.strip()
            if (
                not line
                or len(line) > 60
                or _MARKER_RE.match(line)
                or _is_technical_line(line)
                or _should_preserve_from_frequency(line)
            ):
                continue
            seen_in_section.add(line)
        for line in seen_in_section:
            counts[line] = counts.get(line, 0) + 1

    threshold = total * 0.60
    noise_lines = {line.lower() for line, count in counts.items() if count > threshold}
    if stem:
        noise_lines.add(stem)
    return noise_lines


def clean_extracted_text(text: str, filename: str = "") -> str:
    """Elimina ruido tipico de OCR/extraccion manteniendo contenido tecnico."""
    chars_entrada = len(text or "")
    clean = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    if not clean.strip():
        print(f"[CLEANER] Entrada: {chars_entrada} chars → Salida: 0 chars")
        print("[CLEANER] Líneas eliminadas por frecuencia: 0")
        print("[CLEANER] Líneas eliminadas por regex: 0")
        return ""

    sections = _split_sections(clean)
    structural_noise_lines = _compute_structural_noise_lines(sections, filename=filename)
    cleaned_lines: list[str] = []
    n_eliminadas_frecuencia = 0
    n_eliminadas_regex = 0

    for raw_line in clean.split("\n"):
        line = raw_line.strip()
        if not line:
            cleaned_lines.append("")
            continue

        if _MARKER_RE.match(line):
            cleaned_lines.append(line)
            continue

        is_technical = _is_technical_line(line)

        should_drop = False
        if not is_technical:
            if _PAGE_NUMBER_RE.match(line):
                should_drop = True
                n_eliminadas_regex += 1
            elif _FILLER_RE.match(line):
                should_drop = True
                n_eliminadas_regex += 1
            elif _URL_ONLY_RE.match(line):
                should_drop = True
                n_eliminadas_regex += 1
            elif _SLIDE_META_RE.match(line):
                should_drop = True
                n_eliminadas_regex += 1
            elif len(line) <= 60 and line.lower() in structural_noise_lines:
                should_drop = True
                n_eliminadas_frecuencia += 1

        if should_drop:
            continue

        normalized = _MULTISPACE_RE.sub(r"\1 \2", line)
        cleaned_lines.append(normalized)

    cleaned_text = "\n".join(cleaned_lines)
    cleaned_text = _MULTINEWLINES_RE.sub("\n\n", cleaned_text)
    resultado = cleaned_text.strip()
    print(f"[CLEANER] Entrada: {chars_entrada} chars → Salida: {len(resultado)} chars")
    print(f"[CLEANER] Líneas eliminadas por frecuencia: {n_eliminadas_frecuencia}")
    print(f"[CLEANER] Líneas eliminadas por regex: {n_eliminadas_regex}")
    return resultado
