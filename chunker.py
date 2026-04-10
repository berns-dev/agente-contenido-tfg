"""Division de texto en chunks coherentes."""

from __future__ import annotations

import re

from config import CHUNK_CHAR_RATIO, CHUNK_TARGET_TOKENS


_NUMBERED_HEADER_RE = re.compile(r"^\d+(?:\.\d+)*\.\s+\S")
_PAGE_SLIDE_HEADER_RE = re.compile(r"^\[(?:PAGINA|SLIDE)\s+\d+\]")
_SECTION_KEYWORDS = (
    "Chapter",
    "Section",
    "Topic",
    "Tema",
    "Capitulo",
    "Capítulo",
    "Seccion",
    "Sección",
    "Introduccion",
    "Introducción",
    "Introduction",
    "Summary",
    "Resumen",
    "Ejercicios",
    "Exercises",
    "Problems",
    "Ejemplos",
    "Examples",
)


def _split_large_section_by_paragraph(section: str, max_chars: int) -> list[str]:
    paragraphs = [p.strip() for p in section.strip().split("\n\n") if p.strip()]
    if not paragraphs:
        return []
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for para in paragraphs:
        add_len = len(para) + (2 if current else 0)
        if current and current_len + add_len > max_chars:
            chunks.append("\n\n".join(current).strip())
            current = [para]
            current_len = len(para)
        else:
            current.append(para)
            current_len += add_len
    if current:
        chunks.append("\n\n".join(current).strip())
    return chunks


def _is_section_header(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if _NUMBERED_HEADER_RE.match(stripped):
        return True
    if _PAGE_SLIDE_HEADER_RE.match(stripped):
        return True
    lowered = stripped.lower()
    if any(lowered.startswith(keyword.lower()) for keyword in _SECTION_KEYWORDS):
        return True
    if 4 < len(stripped) < 80 and stripped == stripped.upper():
        return True
    return False


def _split_into_semantic_sections(text: str) -> list[tuple[str | None, str]]:
    lines = text.splitlines()
    sections: list[tuple[str | None, str]] = []
    current_lines: list[str] = []
    current_header: str | None = None
    found_header = False

    for line in lines:
        stripped = line.strip()
        if _is_section_header(stripped):
            found_header = True
            if current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    sections.append((current_header, content))
            current_header = stripped
            current_lines = [stripped]
        else:
            current_lines.append(line)

    if current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            sections.append((current_header, content))

    if not found_header:
        return []
    return sections


def _split_large_semantic_section(section: str, header: str | None, max_chars: int) -> list[str]:
    if not header:
        return _split_large_section_by_paragraph(section, max_chars)

    body = section.split("\n", 1)[1].strip() if "\n" in section else ""
    body_max_chars = max(400, max_chars - len(header) - 1)
    body_chunks = _split_large_section_by_paragraph(body, body_max_chars) if body else []
    if not body_chunks:
        return [header]
    return [f"{header}\n{chunk}".strip() for chunk in body_chunks]


def split_into_chunks(text: str, target_tokens: int | None = None) -> list[str]:
    """
    Divide texto en bloques cercanos a ~1500 tokens.
    Aproximacion: tokens * 4 chars.
    """
    clean = (text or "").strip()
    if not clean:
        return []

    tokens = target_tokens or CHUNK_TARGET_TOKENS
    max_chars = max(1000, tokens * CHUNK_CHAR_RATIO)

    semantic_sections = _split_into_semantic_sections(clean)
    if semantic_sections:
        chunks: list[str] = []
        current_parts: list[str] = []
        current_len = 0

        for header, section in semantic_sections:
            section_len = len(section)
            if header and current_parts and current_len >= 500:
                chunks.append("\n\n".join(current_parts).strip())
                current_parts = []
                current_len = 0

            if section_len > max_chars:
                if current_parts:
                    chunks.append("\n\n".join(current_parts).strip())
                    current_parts = []
                    current_len = 0
                chunks.extend(_split_large_semantic_section(section, header, max_chars))
                continue
            add_len = section_len + (2 if current_parts else 0)
            if current_parts and current_len + add_len > max_chars:
                chunks.append("\n\n".join(current_parts).strip())
                current_parts = [section]
                current_len = section_len
            else:
                current_parts.append(section)
                current_len += add_len
        if current_parts:
            chunks.append("\n\n".join(current_parts).strip())
        return chunks

    paragraphs = [p.strip() for p in clean.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for para in paragraphs:
        add_len = len(para) + (2 if current else 0)
        if current and current_len + add_len > max_chars:
            chunks.append("\n\n".join(current).strip())
            current = [para]
            current_len = len(para)
        else:
            current.append(para)
            current_len += add_len

    if current:
        chunks.append("\n\n".join(current).strip())

    return chunks
