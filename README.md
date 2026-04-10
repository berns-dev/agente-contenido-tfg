# Agente de Limpieza y Curación de Contenido

Convierte material docente (PDF/PPTX) a Markdown estructurado y limpio.
No genera contenido nuevo: solo transforma la representación del contenido existente.

## Instalación
pip install -r requirements.txt
cp .env.example .env
# Edita .env y añade tu ANTHROPIC_API_KEY

## Uso
streamlit run app.py

## Stack
- Python + Streamlit
- Anthropic API (claude-haiku-4-5-20251001 / claude-sonnet-4-5)
- pdfplumber, python-pptx

## Parte del TFG
"Metodologías de Ingeniería Aumentada: Desarrollo de Herramientas de
Cálculo y Aplicaciones Interactivas mediante Agentes de IA"
