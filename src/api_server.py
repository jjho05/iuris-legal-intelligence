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


class LftCalculationRequest(BaseModel):
    antiguedad_anios: int = Field(ge=1, le=50, default=1)
    salario_mensual: float = Field(gt=0, default=25000.0)
    causal: str = Field(default="despido_injustificado")


class QueryRequest(BaseModel):
    pregunta: str
    corpus_id: Optional[str] = None
    enable_web_search: bool = True
    api_key_override: Optional[str] = None


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
async def upload_document(
    file: Optional[UploadFile] = File(None),
    archivo: Optional[UploadFile] = File(None)
):
    """
    Recibe archivos PDF, Word (.docx), TXT o Markdown, extrae su texto,
    lo convierte automáticamente a formato Markdown estructurado (.md)
    e indexa el contenido en el motor RAG para análisis inmediato.
    """
    target_file = file or archivo
    if not target_file:
        raise HTTPException(status_code=400, detail="No se recibió ningún archivo (campo 'file' o 'archivo').")

    try:
        file_bytes = await target_file.read()
        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="El archivo recibido está vacío.")

        # Procesar y convertir a Markdown
        resultado = document_processor.process_file(file_bytes, target_file.filename)

        # Indexar automáticamente en el pipeline
        pipeline_legal.ingest_uploaded_document(target_file.filename, resultado["markdown"])

        return {
            "status": "success",
            "mensaje": f"Documento '{target_file.filename}' procesado y convertido a Markdown con éxito.",
            "archivo": target_file.filename,
            "nombre_archivo": target_file.filename,
            "tipo": resultado["tipo_documento"],
            "archivo_md": resultado["archivo_md"],
            "caracteres": resultado["caracteres"],
            "palabras": resultado["palabras"],
            "secciones_detectadas": resultado["secciones_detectadas"],
            "markdown": resultado["markdown"],
            "contenido_markdown": resultado["markdown"],
            "estadisticas": {
                "tipo": resultado["tipo_documento"],
                "total_palabras": resultado["palabras"],
                "total_caracteres": resultado["caracteres"],
                "total_secciones_detectadas": resultado["secciones_detectadas"]
            }
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


@app.get("/api/corpora", tags=["Conocimiento"])
async def get_corpora():
    """Lista de marcos normativos disponibles y activos."""
    return {
        "status": "ok",
        "corpus_activo": pipeline_legal.rag_engine.current_corpus_id,
        "documento_personalizado": pipeline_legal.rag_engine.active_custom_doc,
        "corpora": [
            {
                "id": "corporativo",
                "nombre": "Estatutos y Gobierno Corporativo",
                "descripcion": "Marco normativo interno para sociedades mercantiles, poderes, rescisión, auditoría y NDA.",
                "icono": "scale",
                "articulos_estimados": 6,
                "es_activo": pipeline_legal.rag_engine.current_corpus_id == "corporativo" and not pipeline_legal.rag_engine.active_custom_doc
            },
            {
                "id": "lft",
                "nombre": "Ley Federal del Trabajo (LFT)",
                "descripcion": "Reformas clave: Vacaciones Dignas (Art. 76), Aguinaldo (Art. 87), Indemnización (Art. 48/50), Teletrabajo (330-A) y Rescisión (47).",
                "icono": "users",
                "articulos_estimados": 8,
                "es_activo": pipeline_legal.rag_engine.current_corpus_id == "lft" and not pipeline_legal.rag_engine.active_custom_doc
            }
        ]
    }


@app.get("/api/corpus/preview", tags=["Conocimiento"])
async def get_corpus_preview(corpus_id: Optional[str] = None):
    """Devuelve el texto completo, artículos e índice para el visor de expedientes."""
    cid = corpus_id or pipeline_legal.rag_engine.current_corpus_id
    if cid == "lft":
        path = BASE_DIR / "data" / "lft_reformas_clave.txt"
        title = "Ley Federal del Trabajo — Reformas Fundamentales"
    elif cid == "custom" and pipeline_legal.rag_engine.active_custom_doc:
        content = "\n\n".join(pipeline_legal.rag_engine.documentos)
        return {
            "status": "ok",
            "corpus_id": "custom",
            "titulo": pipeline_legal.rag_engine.active_custom_doc,
            "preview_texto": content,
            "total_articulos": len(pipeline_legal.rag_engine.documentos),
            "total_palabras": len(content.split()),
            "total_caracteres": len(content)
        }
    else:
        path = settings.CORPUS_FILE_PATH
        title = "Estatutos Corporativos y Código de Cumplimiento"

    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = "\n\n".join(pipeline_legal.rag_engine.documentos)

    return {
        "status": "ok",
        "corpus_id": cid,
        "titulo": title,
        "preview_texto": content,
        "total_articulos": len(pipeline_legal.rag_engine.documentos),
        "total_palabras": len(content.split()),
        "total_caracteres": len(content)
    }


@app.get("/api/dossier/markdown", tags=["Conocimiento"])
async def get_dossier_markdown(corpus_id: Optional[str] = None):
    """Descarga o lectura del expediente en formato Markdown estándar."""
    cid = corpus_id or pipeline_legal.rag_engine.current_corpus_id
    if cid == "lft":
        path = BASE_DIR / "data" / "lft_reformas_clave.txt"
        fname = "ley_federal_del_trabajo_vigente"
    elif cid == "custom" and pipeline_legal.rag_engine.active_custom_doc:
        content = "\n\n".join(pipeline_legal.rag_engine.documentos)
        return {
            "status": "ok",
            "filename": pipeline_legal.rag_engine.active_custom_doc,
            "markdown": content
        }
    else:
        path = settings.CORPUS_FILE_PATH
        fname = "estatutos_corporativos_base"

    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = "\n\n".join(pipeline_legal.rag_engine.documentos)

    return {
        "status": "ok",
        "filename": fname,
        "markdown": content
    }


@app.post("/api/calculator/lft", tags=["Herramientas Periciales"])
async def calculate_lft(req: LftCalculationRequest):
    """Calcula liquidaciones e indemnizaciones conforme a la Ley Federal del Trabajo."""
    anios = req.antiguedad_anios
    salario = req.salario_mensual
    sdo = salario / 30.0

    if anios == 1:
        dias = 12
    elif anios == 2:
        dias = 14
    elif anios == 3:
        dias = 16
    elif anios == 4:
        dias = 18
    elif anios == 5:
        dias = 20
    elif anios <= 10:
        dias = 22
    elif anios <= 15:
        dias = 24
    else:
        dias = 26

    factor_integracion = 1.0 + (15.0 / 365.0) + ((dias * 0.25) / 365.0)
    sdi = sdo * factor_integracion

    pago_vacaciones = sdo * dias
    prima_vacacional = pago_vacaciones * 0.25
    aguinaldo = sdo * 15.0
    subtotal_finiquito = pago_vacaciones + prima_vacacional + aguinaldo

    tope_smg = 497.86  # 2 Salarios Mínimos Generales 2024
    salario_base_prima = min(sdo, tope_smg)
    prima_antiguedad_total = 12.0 * anios * salario_base_prima

    indemnizacion_90_dias = 0.0
    veinte_dias_por_anio = 0.0
    prima_aplicable = 0.0

    if req.causal == "despido_injustificado":
        indemnizacion_90_dias = 90.0 * sdi
        veinte_dias_por_anio = 20.0 * anios * sdi
        prima_aplicable = prima_antiguedad_total
        total = indemnizacion_90_dias + veinte_dias_por_anio + prima_aplicable + subtotal_finiquito
    elif req.causal == "renuncia_voluntaria":
        if anios >= 15:
            prima_aplicable = prima_antiguedad_total
        total = subtotal_finiquito + prima_aplicable
    else:
        total = subtotal_finiquito

    return {
        "status": "ok",
        "antiguedad_anios": anios,
        "salario_mensual": salario,
        "sdo": round(sdo, 2),
        "sdi": round(sdi, 2),
        "factor_integracion": round(factor_integracion, 4),
        "dias_vacaciones": dias,
        "pago_vacaciones": round(pago_vacaciones, 2),
        "prima_vacacional": round(prima_vacacional, 2),
        "aguinaldo": round(aguinaldo, 2),
        "subtotal_finiquito": round(subtotal_finiquito, 2),
        "indemnizacion_90_dias": round(indemnizacion_90_dias, 2),
        "veinte_dias_por_anio": round(veinte_dias_por_anio, 2),
        "prima_antiguedad": round(prima_aplicable, 2),
        "total_liquidacion": round(total, 2),
        "fundamentos_legales": [
            "Art. 76 LFT (Vacaciones Dignas)",
            "Art. 80 LFT (Prima Vacacional 25%)",
            "Art. 84 y 89 LFT (Salario Diario Integrado)",
            "Art. 87 LFT (Aguinaldo 15 días)",
            "Art. 48 y 50 LFT (Indemnización Constitucional y 20 días por año)" if req.causal == "despido_injustificado" else "Art. 47 LFT (Rescisión sin responsabilidad patronal)",
            "Art. 162 LFT (Prima de Antigüedad)"
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


@app.post("/api/query", tags=["Inferencia"])
async def query_endpoint(req: QueryRequest, x_gemini_key: Optional[str] = Header(None)):
    """Consulta pericial con matriz de riesgos, fundamentación jurídica y grounding web."""
    chat_req = ChatRequest(
        mensaje=req.pregunta,
        enable_web_search=req.enable_web_search,
        corpus=req.corpus_id,
        api_key_override=req.api_key_override
    )
    resp = await chat_endpoint(chat_req, x_gemini_key=x_gemini_key)
    
    texto_resp = resp.respuesta.lower()
    riesgo_alto = any(k in texto_resp for k in ["grave", "rescisión", "penalización", "violación", "indemnización", "riesgo alto", "ilegal", "nulo"])
    riesgo_medio = any(k in texto_resp for k in ["observación", "ambigüedad", "plazo", "notificación", "contingencia", "cautela"])
    nivel_riesgo = "ALTO" if riesgo_alto else ("MEDIO" if riesgo_medio else "BAJO")
    
    return {
        "status": "ok",
        "respuesta": resp.respuesta,
        "ruta": resp.ruta,
        "fuentes": resp.fuentes,
        "confianza": resp.confianza,
        "fuentes_web": resp.fuentes_web,
        "metadatos": resp.metadatos,
        "matriz_riesgos": {
            "nivel_riesgo_general": nivel_riesgo,
            "clausulas_analizadas": len(resp.fuentes) or 1,
            "alertas": [
                {
                    "categoria": "Penalización & Rescisión Contractual",
                    "nivel": "CRÍTICO" if "penalización" in texto_resp or "rescisión" in texto_resp else "OK",
                    "fundamento": "Art. 47 LFT / Cláusula de Rescisión Contractual"
                },
                {
                    "categoria": "Confidencialidad y Secretos Industriales",
                    "nivel": "ALTO" if "confidencialidad" in texto_resp or "secreto" in texto_resp else "MEDIO",
                    "fundamento": "Ley Federal de Protección a la Propiedad Industrial"
                },
                {
                    "categoria": "Cumplimiento Laboral y Prestaciones",
                    "nivel": "MONITOREO",
                    "fundamento": "Art. 76, 80 & 87 LFT"
                }
            ]
        }
    }


# Montaje de estáticos
public_dir = BASE_DIR / "public"
if public_dir.exists():
    app.mount("/", StaticFiles(directory=str(public_dir), html=True), name="public")
