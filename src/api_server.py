"""
Microservicio REST Asíncrono con FastAPI (api_server.py).
Soporta subida y conversión de PDF/DOCX a Markdown (/api/upload), chat fáctico con búsqueda web,
extracción LoRA JSON, y despliegue serverless en Vercel.
"""

import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, status, Header, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.config import settings, BASE_DIR
from src.pipeline import pipeline_legal
from src.document_processor import document_processor

# Inicialización de la aplicación FastAPI
app = FastAPI(
    title="Iuris Legal Intelligence — API de Cumplimiento & Contratos",
    description="Plataforma de análisis de contratos, legislación vigente con búsqueda web y Google Gemini 3.8 Flash.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url=None
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# ESQUEMAS PYDANTIC
# ==============================================================================

class ChatRequest(BaseModel):
    mensaje: str = Field(
        ...,
        min_length=2,
        max_length=2500,
        description="Consulta del usuario sobre estatutos, políticas, LFT o contratos",
        examples=["¿Cuál es el periodo de vacaciones mínimas según la reforma de la LFT?"]
    )
    enable_web_search: bool = Field(default=True, description="Habilita búsqueda web de leyes vigentes")
    corpus: Optional[str] = Field(default=None, description="Marco normativo: 'corporativo', 'lft' o 'custom'")
    api_key_override: Optional[str] = Field(default=None)


class ChatResponse(BaseModel):
    respuesta: str = Field(description="Respuesta jurídica fundamentada")
    ruta: str = Field(description="Ruta de ejecución del sistema")
    fuentes: List[str] = Field(default=[], description="Artículos, cláusulas o leyes citadas")
    confianza: float = Field(description="Nivel de certidumbre")
    fuentes_web: Optional[List[Dict[str, Any]]] = Field(default=[], description="Leyes y fuentes de internet")
    metadatos: Dict[str, Any] = Field(default={}, description="Telemetría")


class ExtractRequest(BaseModel):
    texto: str = Field(
        ...,
        min_length=10,
        max_length=4000,
        description="Fragmento de contrato o cláusula a analizar"
    )
    api_key_override: Optional[str] = Field(default=None)


class ExtractResponse(BaseModel):
    dictamen: Dict[str, Any] = Field(description="Objeto JSON estructurado tipado")
    latencia_ms: float = Field(description="Tiempo de procesamiento en milisegundos")
    modelo: str = Field(description="Modelo utilizado")


class SelectCorpusRequest(BaseModel):
    corpus_id: str = Field(description="'corporativo' o 'lft'")


# ==============================================================================
# ENDPOINTS REST
# ==============================================================================

@app.get("/health", tags=["Monitoreo"])
@app.get("/api/health", tags=["Monitoreo"])
async def health_check():
    """Estado del servicio y modelos activos."""
    total_docs = len(pipeline_legal.rag_engine.documentos)
    return {
        "status": "ok",
        "version": "2.0.0",
        "gemini_configurado": settings.is_gemini_configured,
        "gemini_modelo": settings.GEMINI_MODEL,
        "corpus_activo": pipeline_legal.rag_engine.current_corpus_id,
        "documento_personalizado": pipeline_legal.rag_engine.active_custom_doc,
        "total_secciones_indexadas": total_docs,
        "total_articulos_indexados": total_docs
    }


@app.post("/api/upload", tags=["Ingestión de Documentos"])
async def upload_document(file: UploadFile = File(...)):
    """
    Recibe archivos PDF, Word (.docx), TXT o Markdown, extrae su texto,
    lo convierte automáticamente a formato Markdown estructurado (.md)
    e indexa el contenido en el motor RAG para análisis inmediato.
    """
    try:
        file_bytes = await file.read()
        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="El archivo recibido está vacío.")

        # Procesar y convertir a Markdown
        resultado = document_processor.process_file(file_bytes, file.filename)

        # Indexar automáticamente en el pipeline
        pipeline_legal.ingest_uploaded_document(file.filename, resultado["markdown"])

        return {
            "status": "success",
            "mensaje": f"Documento '{file.filename}' procesado y convertido a Markdown con éxito.",
            "archivo": file.filename,
            "tipo": resultado["tipo_documento"],
            "archivo_md": resultado["archivo_md"],
            "caracteres": resultado["caracteres"],
            "palabras": resultado["palabras"],
            "secciones_detectadas": resultado["secciones_detectadas"],
            "markdown": resultado["markdown"]
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fallo al procesar el documento: {str(e)}")


@app.post("/api/corpus/select", tags=["Conocimiento"])
async def select_corpus(request: SelectCorpusRequest):
    """Permite alternar entre marcos normativos (ej. Corporativo vs Ley Federal del Trabajo)."""
    if request.corpus_id not in {"corporativo", "lft"}:
        raise HTTPException(status_code=400, detail="Corpus no reconocido. Opciones: 'corporativo', 'lft'.")
    pipeline_legal.set_corpus(request.corpus_id)
    return {
        "status": "ok",
        "corpus_activo": request.corpus_id,
        "total_secciones": len(pipeline_legal.rag_engine.documentos)
    }


@app.get("/api/corpus", tags=["Conocimiento"])
async def get_corpus():
    """Devuelve las secciones y artículos del marco legal o documento actualmente cargado."""
    return {
        "corpus_id": pipeline_legal.rag_engine.current_corpus_id,
        "documento_activo": pipeline_legal.rag_engine.active_custom_doc,
        "total_secciones": len(pipeline_legal.rag_engine.documentos),
        "secciones": [
            {
                "indice": i + 1,
                "titulo": pipeline_legal.rag_engine.titulos[i] if i < len(pipeline_legal.rag_engine.titulos) else f"Sección {i+1}",
                "contenido": doc
            }
            for i, doc in enumerate(pipeline_legal.rag_engine.documentos)
        ]
    }


@app.post("/v1/chat", response_model=ChatResponse, tags=["Inferencia"])
@app.post("/api/chat", response_model=ChatResponse, tags=["Inferencia"])
async def chat_endpoint(request: ChatRequest, x_gemini_key: Optional[str] = Header(None)):
    """Inferencia conversacional con Grounding Web de leyes y análisis RAG."""
    try:
        active_key = request.api_key_override or x_gemini_key
        if active_key and not settings.is_gemini_configured:
            pipeline_legal.gemini_client.api_key = active_key
            pipeline_legal.gemini_client._client_initialized = True

        resultado = pipeline_legal.procesar_consulta(
            query=request.mensaje,
            enable_web_search=request.enable_web_search,
            active_corpus=request.corpus
        )

        return ChatResponse(
            respuesta=resultado["respuesta"],
            ruta=resultado["ruta"],
            fuentes=resultado.get("fuentes", []),
            confianza=resultado.get("confianza", 0.0),
            fuentes_web=resultado.get("fuentes_web", []),
            metadatos=resultado.get("metadatos", {})
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en inferencia: {str(e)}")


@app.post("/v1/extract", response_model=ExtractResponse, tags=["Extracción Estructurada"])
@app.post("/api/extract", response_model=ExtractResponse, tags=["Extracción Estructurada"])
async def extract_endpoint(request: ExtractRequest):
    """Extracción estructurada de contratos en JSON tipado."""
    try:
        t0 = time.perf_counter()
        dictamen = pipeline_legal.lora_adapter.extract(request.texto)
        latencia = round((time.perf_counter() - t0) * 1000, 2)
        return ExtractResponse(
            dictamen=dictamen,
            latencia_ms=latencia,
            modelo=settings.GEMINI_MODEL
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en extracción: {str(e)}")


# Montaje de estáticos
public_dir = BASE_DIR / "public"
if public_dir.exists():
    app.mount("/", StaticFiles(directory=str(public_dir), html=True), name="public")
