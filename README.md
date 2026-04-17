# Agente de Contenido

Este repositorio forma parte de un Trabajo Fin de Grado (TFG) de la Universidad de Oviedo sobre metodologías de ingeniería aumentadas con IA. Se complementa con el repositorio hermano `agente-organizador-tfg`.

## Qué hace

Este agente está orientado a profesorado universitario que quiere convertir material docente en un formato editable y trazable sin alterar su contenido. Recibe documentos PDF o PPTX y produce un único archivo Markdown estructurado y limpio, preservando fielmente la información original.

El resultado clasifica cada bloque como teoría, ejemplo resuelto, ejercicio propuesto, tabla o procedimiento. El sistema no resume, no infiere y no añade información nueva: únicamente reorganiza y normaliza lo que ya está en los documentos de entrada.

## Decisiones de diseño para contexto académico

La selección de modelo se hace por heurística según el tipo de fragmento detectado. Se utiliza Haiku cuando el contenido es texto plano y Sonnet cuando el bloque contiene ecuaciones o notación matemática densa, con el objetivo de mantener precisión formal en la transcripción.

Después del ensamblado, se aplica un validador de fidelidad léxica. Este paso comprueba que los términos técnicos clave del original aparezcan también en la salida y exige superar un umbral configurable de 0.85 para aceptar el resultado.

La segmentación es semántica y respeta los límites naturales del material fuente. En la práctica, esto significa que el procesamiento conserva fronteras de página en PDF y de diapositiva en PPTX para evitar mezclar contexto de secciones distintas.

## Limitaciones conocidas y documentadas

Cuando una presentación de PowerPoint se exporta a PDF, el proceso de exportación suele destruir la estructura semántica interna (encabezados, jerarquía de viñetas y tablas). Esa información no puede recuperarse de forma fiable con bibliotecas de extracción de texto, porque se pierde en el propio formato exportado.

El agente detecta esta situación y muestra una advertencia en la interfaz, recomendando subir el archivo PPTX original. Esta limitación pertenece al formato PDF resultante de la exportación y no a un fallo del agente.

## Compatibilidad entre agentes

La salida Markdown incluye un frontmatter YAML con `compatible_agente_organizador: true`. Esto permite usar directamente el archivo generado como entrada en `agente-organizador-tfg`, aunque su uso es opcional y no condiciona el funcionamiento del agente de contenido.

## Estado actual de implementación

El extractor lee PDF y PPTX y obtiene el texto base junto con metadatos de origen. El cleaner normaliza caracteres, espacios y artefactos de extracción para preparar una base consistente. El chunker divide el contenido en unidades semánticas respetando límites de página o diapositiva. El classifier asigna a cada bloque su categoría funcional (teoría, ejemplo, ejercicio, tabla o procedimiento). El assembler construye un único Markdown final con estructura homogénea. El validator ejecuta la comprobación de fidelidad léxica y marca si se cumple el umbral configurado.

## Instalación y ejecución

Clonación y preparación del entorno:

```bash
git clone https://github.com/berns-dev/agente-contenido-tfg.git
cd agente-contenido-tfg
python -m venv .venv
```

En Windows (PowerShell):

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

En macOS/Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edite `.env` e indique su clave:

```env
ANTHROPIC_API_KEY=su_clave_aqui
```

Para iniciar la aplicación:

```bash
streamlit run app.py
```

## Estructura del proyecto

`app.py` implementa la interfaz en Streamlit y orquesta la carga de archivos, el procesamiento y la descarga del resultado. `extractor.py` obtiene texto y metadatos desde PDF/PPTX como base del pipeline. `cleaner.py` normaliza artefactos de extracción y prepara una representación estable del contenido. `chunker.py` divide el material en fragmentos semánticos respetando límites de página o diapositiva. `classifier.py` asigna la categoría funcional de cada bloque (teoría, ejemplo, ejercicio, tabla o procedimiento). `assembler.py` construye el Markdown final unificado. `validator.py` verifica la fidelidad léxica frente al original según el umbral configurado.
