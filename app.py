"""UI Streamlit para el pipeline de Agente_contenido."""

from __future__ import annotations

import tempfile
from collections import Counter
from pathlib import Path

import streamlit as st

from assembler import assemble_markdown, assemble_multiple, unified_download_filename
from chunker import split_into_chunks
from classifier import classify_and_format
from extractor import extract_text
from validator import validate_items


def main() -> None:
    if "resultados" not in st.session_state:
        st.session_state["resultados"] = []
    if "archivos_hash" not in st.session_state:
        st.session_state["archivos_hash"] = tuple()

    st.set_page_config(page_title="Agente contenido", layout="wide")

    st.title("Agente_contenido")
    st.caption("Extraccion, chunking, clasificacion y ensamblado Markdown.")

    uploaded_files = st.file_uploader(
        "Sube uno o varios archivos (PDF o PPTX)",
        type=["pdf", "pptx"],
        accept_multiple_files=True,
    )
    files: list = list(uploaded_files) if uploaded_files else []
    current_files_hash = tuple(sorted(f.name for f in files))

    if files and any(Path(f.name).suffix.lower() == ".pdf" for f in files):
        st.warning(
            "Si este archivo es una presentación exportada desde PowerPoint, los "
            "resultados serán limitados. Para mejor fidelidad, sube el archivo "
            ".pptx original."
        )

    for f in files:
        st.caption(f"{f.name}")

    if files:
        if st.button("Procesar"):
            st.session_state["resultados"] = []
            st.session_state["archivos_hash"] = current_files_hash

            for uploaded in files:
                name = uploaded.name
                stem = Path(name).stem
                tmp_path: str | None = None
                with st.status(name, expanded=True) as status:
                    try:
                        suffix = Path(name).suffix
                        with tempfile.NamedTemporaryFile(
                            delete=False, suffix=suffix
                        ) as tmp:
                            tmp.write(uploaded.getbuffer())
                            tmp_path = tmp.name

                        status.write("Extracción…")
                        text = extract_text(tmp_path)

                        status.write("Chunks…")
                        chunks = split_into_chunks(text)

                        status.write("Clasificación…")
                        items = [classify_and_format(chunk) for chunk in chunks]

                        status.write("Ensamblado…")
                        output_md = assemble_markdown(
                            items, nombre_del_archivo=name
                        )

                        status.write("Validación…")
                        report = validate_items(items, original_chunks=chunks)

                        st.session_state["resultados"].append(
                            {
                                "nombre": name,
                                "stem": stem,
                                "markdown": output_md,
                                "items": items,
                                "validacion": report,
                                "error": None,
                            }
                        )

                        status.update(
                            label=f"Completado: {name}",
                            state="complete",
                        )
                    except Exception as exc:  # noqa: BLE001
                        status.update(
                            label=f"Error: {name}",
                            state="error",
                        )
                        status.write(str(exc))
                        st.session_state["resultados"].append(
                            {
                                "nombre": name,
                                "stem": stem,
                                "markdown": "",
                                "items": [],
                                "validacion": {},
                                "error": str(exc),
                            }
                        )
                    finally:
                        if tmp_path:
                            try:
                                Path(tmp_path).unlink(missing_ok=True)
                            except OSError:
                                pass

    if st.session_state["resultados"]:
        if current_files_hash != st.session_state.get("archivos_hash", tuple()):
            st.warning(
                "⚠️ Los archivos han cambiado. Pulsa 'Procesar' para actualizar los resultados."
            )

        ok = [r for r in st.session_state["resultados"] if not r.get("error")]
        if len(ok) > 1:
            unified_md = assemble_multiple(ok)
            n_ok = len(ok)
            unified_fn = unified_download_filename([r["stem"] for r in ok])
            st.download_button(
                label=f"⬇️ Descargar todo unificado ({n_ok} archivos)",
                data=unified_md,
                file_name=unified_fn,
                mime="text/markdown",
                key="dl_unificado",
            )
            st.divider()

        for i, res in enumerate(st.session_state["resultados"]):
            with st.expander(res["nombre"], expanded=True):
                if res["error"]:
                    st.error(f"Error: {res['error']}")
                else:
                    lineas_frontmatter = [
                        ln
                        for ln in res["markdown"].split("\n")
                        if ln.startswith(
                            (
                                "archivo_origen",
                                "tipo_documento",
                                "idioma",
                                "tema_detectado",
                                "fecha_procesado",
                            )
                        )
                    ]
                    for linea in lineas_frontmatter:
                        st.caption(linea)

                    n_bloques = len(res["items"])
                    tipos = [it.get("tipo", "?") for it in res["items"]]
                    conteo = Counter(tipos)
                    resumen = " · ".join(f"{v} {k}" for k, v in conteo.items())
                    st.caption(f"Bloques generados: {n_bloques} ({resumen})")

                    st.download_button(
                        label=f"⬇️ Descargar {res['stem']}_curado.md",
                        data=res["markdown"],
                        file_name=f"{res['stem']}_curado.md",
                        mime="text/markdown",
                        key=f"dl_{i}",
                    )

                    with st.expander("Ver reporte de fidelidad", expanded=False):
                        st.json(res["validacion"])


if __name__ == "__main__":
    main()
