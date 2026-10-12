# Iuris Legal Intelligence — Suite de Cumplimiento & Análisis Contractual

> **Proyecto Oficial — Hackathon 1:** Sistema de grado empresarial para auditoría de contratos, dictamen de riesgos legales y consulta de legislación federal vigente (Ley Federal del Trabajo, estatutos corporativos y expedientes privados) impulsado por **Google Gemini 3.8 Flash**, RAG vectorial y Grounding Web en tiempo real.

---

## 1. Capacidades Principales

* **Modelo Base Oficial:** Configurado por defecto con `gemini-3.8-flash`, garantizando respuestas fácticas de alta velocidad y rigor pericial.
* **Ingestión y Conversión de Archivos a Markdown (.md):**
  * Soporte nativo para contratos y leyes en formato **PDF (.pdf)** y **Microsoft Word (.docx)**.
  * Extracción automática, limpieza de texto y conversión estructurada a **Markdown (.md)** (encabezados jerárquicos, cláusulas, listas y tablas).
  * Indexación en caliente para formular preguntas o solicitar dictámenes sobre el documento cargado al instante.
* **Corpus Normativo Dinámico:**
  * No está restringido a un estatuto fijo: permite alternar entre el **Estatuto Corporativo Base**, la **Ley Federal del Trabajo (LFT / Reformas Laborales)** o el **Expediente / Contrato subido por el usuario**.
* **Búsqueda Web en Vivo (Grounding Jurídico):**
  * Conexión con internet para contrastar leyes vigentes, decretos del Diario Oficial de la Federación (DOF) y jurisprudencias en tiempo real, citando enlaces oficiales (ej. `diputados.gob.mx`).
* **Diseño Editorial Ejecutivo (Cero "Vibecoding"):**
  * Interfaz sobria, distinguida y profesional (estilo *Harvey AI / CoCounsel / Casetext*).
  * Sin elementos fluorescentes, sin badges fosforescentes y sin enlaces a Swagger en la interfaz pública.
* **100% Responsivo Móvil (Mobile-First):**
  * Experiencia adaptada tanto a estaciones de trabajo como a tablets y smartphones.
  * Drawer lateral deslizable para visualización del expediente y citas normativas en pantallas táctiles, con soporte para áreas seguras (`safe-area-inset-bottom`).
* **Salidas Estructuradas Tipadas (Pydantic v2):**
  * Extracción de obligaciones, nivel de riesgo legal, plazos de aviso y penalizaciones en JSON validado.

---

## 2. Estructura del Proyecto

```
HACKATHON1/
├── api/
│   └── index.py                      # Punto de entrada Serverless para Vercel
├── data/
│   ├── normativas_corporativas.txt    # Corpus corporativo de referencia
│   ├── lft_reformas_clave.txt        # Corpus esencial de la Ley Federal del Trabajo
│   └── uploads/                      # Directorio de documentos y Markdown generados
├── public/
│   ├── index.html                    # Interfaz web institucional y responsiva
│   ├── style.css                     # Sistema de diseño editorial sobrio
│   └── app.js                        # Lógica de cliente (drag&drop, chat, visor MD)
├── src/
│   ├── __init__.py
│   ├── config.py                     # Configuración tipada (gemini-3.8-flash)
│   ├── document_processor.py         # Extractor y convertidor PDF/Word a Markdown
│   ├── web_search.py                 # Conector de búsqueda en internet para leyes
│   ├── rag_engine.py                 # Motor RAG dinámico multi-corpus
│   ├── gemini_client.py              # Inferencia con Gemini 3.8 Flash y Grounding
│   ├── lora_adapter.py               # Extracción estructurada en JSON
│   ├── router.py                     # Clasificador heurístico de fast-path
│   ├── pipeline.py                   # Orquestador integral
│   └── api_server.py                 # Microservicio REST FastAPI
├── tests/
│   ├── test_document_processor.py    # Pruebas de conversión PDF/Word a Markdown
│   └── test_red_teaming.py           # Suite de pruebas de seguridad y red teaming
├── main.py                           # Servidor local FastAPI / CLI interactivo
├── requirements.txt                  # Dependencias oficiales (pypdf, python-docx, etc.)
├── vercel.json                       # Configuración de despliegue en Vercel
└── .env.example                      # Plantilla de variables de entorno
```

---

## 3. Instalación y Ejecución Local

### Paso 1: Configurar Entorno
```bash
cd HACKATHON1
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Paso 2: Configurar Clave de Gemini (Opcional para modo nube)
Copia `.env.example` a `.env` y agrega tu clave de [Google AI Studio](https://aistudio.google.com/):
```bash
cp .env.example .env
```
*(Nota: Si no configuras la clave, el sistema cuenta con un motor de simulación jurídica determinista local).*

### Paso 3: Iniciar la Aplicación Web
```bash
python3 main.py --port 8000
```
Abre en tu navegador: **`http://localhost:8000`**

---

## 4. Pruebas Automatizadas

Ejecutar la suite completa de 9 pruebas unitarias y de robustez:
```bash
pytest tests/ -v
```

---

## 5. Despliegue en Vercel

1. Instalar Vercel CLI: `npm i -g vercel`
2. En la raíz de `HACKATHON1/`, ejecutar:
   ```bash
   vercel
   ```
3. En el panel de control de Vercel, agregar la variable de entorno:
   * `GEMINI_API_KEY`: tu clave de API de Google AI Studio.
   * `GEMINI_MODEL`: `gemini-3.8-flash`
