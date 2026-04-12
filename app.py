"""UI Streamlit para el pipeline de Agente_contenido."""

from __future__ import annotations

import tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import streamlit as st

from assembler import assemble_markdown, assemble_multiple, unified_download_filename
from chunker import split_into_chunks
from classifier import classify_and_format
from config import MAX_WORKERS
from extractor import extract_text
from validator import validate_items


def main() -> None:
    if "resultados" not in st.session_state:
        st.session_state["resultados"] = []
    if "archivos_hash" not in st.session_state:
        st.session_state["archivos_hash"] = tuple()

    st.set_page_config(page_title="Agente contenido", layout="wide")

    st.markdown(
        """
<style>
[data-testid="stFileUploaderDropzone"] {
    background-color: var(--background-color);
    border-radius: 8px;
}
.stButton > button {
    background-color: #185FA5 !important;
    color: white !important;
    border: none !important;
    border-radius: 7px !important;
    font-weight: 500 !important;
}
.stButton > button:hover {
    background-color: #0C447C !important;
}
.stDownloadButton > button {
    border-radius: 7px !important;
    border-color: rgba(24,95,165,0.4) !important;
    color: #185FA5 !important;
}
.stDownloadButton > button:hover {
    background-color: rgba(24,95,165,0.06) !important;
}
</style>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
<div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">
  <div style="width:34px; height:34px; border-radius:8px; background:#185FA5;
       display:flex; align-items:center; justify-content:center; flex-shrink:0;">
    <svg width="18" height="18" viewBox="0 0 16 16" fill="none"
         stroke="white" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
      <path d="M2 4h12M4 8h8M6 12h4"/>
    </svg>
  </div>
  <div>
    <div style="font-size:15px; font-weight:500;">Agente Contenido</div>
    <div style="font-size:10px; opacity:0.5; margin-top:1px;">TFG</div>
  </div>
</div>
<div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">
  <div style="width:3px; height:24px; background:#185FA5;
       border-radius:2px; flex-shrink:0;"></div>
  <h2 style="font-size:22px; font-weight:500; margin:0;">
    Limpieza y curación de contenido
  </h2>
</div>
<p style="font-size:13px; opacity:0.6; margin:0 0 16px 13px; line-height:1.5;">
  Extracción, chunking, clasificación y ensamblado Markdown a partir de PDF o PPTX.
</p>
""",
        unsafe_allow_html=True,
    )

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

    if files:
        chips_html = "".join(
            f'<span style="display:inline-flex; align-items:center; gap:5px; '
            f'background:rgba(128,128,128,0.08); border:0.5px solid rgba(128,128,128,0.15); '
            f'border-radius:5px; padding:4px 10px; font-size:11px; '
            f'color:var(--text-color); margin:0 4px 4px 0;">'
            f'<span style="width:6px; height:6px; border-radius:50%; '
            f'background:#185FA5; display:inline-block; flex-shrink:0;"></span>'
            f"{f.name}</span>"
            for f in files
        )
        st.markdown(
            f'<div style="display:flex; flex-wrap:wrap; margin-bottom:12px;">'
            f"{chips_html}</div>",
            unsafe_allow_html=True,
        )

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

                        n_chunks = len(chunks)
                        if n_chunks == 0:
                            items = []
                        else:
                            status.write(f"Clasificación… (0/{n_chunks})")
                            ordered: list = [None] * n_chunks
                            done = 0
                            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
                                future_to_i = {
                                    pool.submit(classify_and_format, chunk): i
                                    for i, chunk in enumerate(chunks)
                                }
                                for fut in as_completed(future_to_i):
                                    i = future_to_i[fut]
                                    ordered[i] = fut.result()
                                    done += 1
                                    status.write(
                                        f"Clasificación… ({done}/{n_chunks})"
                                    )
                            items = ordered

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

    if not st.session_state["resultados"] and not files:
        st.info(
            "Sube uno o varios archivos PDF o PPTX y pulsa **Procesar** para comenzar."
        )

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
                label=f"Descargar todo unificado ({n_ok} archivos)",
                data=unified_md,
                file_name=unified_fn,
                mime="text/markdown",
                key="dl_unificado",
            )
            st.divider()

        for i, res in enumerate(st.session_state["resultados"]):
            with st.expander(res["nombre"], expanded=False):
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
                    if lineas_frontmatter:
                        pills_html = "".join(
                            f'<span style="display:inline-block; font-size:11px; '
                            f'background:rgba(128,128,128,0.07); border-radius:4px; '
                            f'padding:3px 8px; margin:0 4px 4px 0; '
                            f'color:var(--text-color); opacity:0.75;">{ln}</span>'
                            for ln in lineas_frontmatter
                        )
                        st.markdown(
                            f'<div style="display:flex; flex-wrap:wrap; margin-bottom:10px;">'
                            f"{pills_html}</div>",
                            unsafe_allow_html=True,
                        )

                    n_bloques = len(res["items"])
                    tipos = [it.get("tipo", "?") for it in res["items"]]
                    conteo = Counter(tipos)
                    resumen = " · ".join(f"{v} {k}" for k, v in conteo.items())
                    col_total, col_rest = st.columns([1, 3])
                    with col_total:
                        st.metric("Bloques totales", n_bloques)
                    with col_rest:
                        st.caption(resumen)

                    st.download_button(
                        label=f"Descargar {res['stem']}_curado.md",
                        data=res["markdown"],
                        file_name=f"{res['stem']}_curado.md",
                        mime="text/markdown",
                        key=f"dl_{i}",
                    )

                    with st.expander("Ver reporte de fidelidad", expanded=False):
                        st.json(res["validacion"])


if __name__ == "__main__":
    main()
