"""
Pipeline Orquestador Integral (pipeline.py).
Coordina Documentos Subidos (PDF/Word), Búsqueda Web de Leyes, Motor RAG y Gemini 3.8 Flash.
"""

import time
import json
from typing import Dict, Any, List, Optional
from src.config import settings
from src.router import ModelRouter
from src.rag_engine import VectorRAGEngine
from src.gemini_client import GeminiLegalClient
from src.lora_adapter import LoRAStructuredAdapter
from src.web_search import web_searcher


class LegalAIPipeline:
    """Orquestador de grado industrial para Iuris Legal Intelligence."""

    def __init__(self):
        print("[PIPELINE] Inicializando suite LegalTech Iuris con Gemini 3.8 Flash...")
        self.router = ModelRouter()
        self.rag_engine = VectorRAGEngine()
        self.gemini_client = GeminiLegalClient()
        self.lora_adapter = LoRAStructuredAdapter(self.gemini_client)
        self.web_searcher = web_searcher
        print("[PIPELINE] Suite jurídica lista.")

    def set_corpus(self, corpus_id: str):
        """Cambia el marco normativo de referencia: 'corporativo', 'lft' o 'custom'."""
        self.rag_engine.load_corpus(corpus_id)

    def ingest_uploaded_document(self, filename: str, markdown_content: str):
        """Indexa un contrato o ley subida por el usuario para análisis inmediato."""
        self.rag_engine.index_custom_markdown(filename, markdown_content)

    def procesar_consulta(
        self,
        query: str,
        enable_web_search: bool = True,
        active_corpus: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta el ciclo de análisis jurídico:
        1. Fast-Path para saludos elementales.
        2. Extracción de contratos a JSON estructurado si se solicita.
        3. Recuperación RAG de cláusulas en el documento o cuerpo legal activo.
        4. Búsqueda web complementaria en leyes y decretos vigentes.
        5. Inferencia con Google Gemini 3.8 Flash.
        """
        t_inicio = time.perf_counter()

        if active_corpus and active_corpus != self.rag_engine.current_corpus_id and active_corpus != "custom":
            self.rag_engine.load_corpus(active_corpus)

        ruta = self.router.route(query)

        # 1. ATATO: Saludo Directo (< 1ms)
        if ruta == "DIRECT_GREETING":
            resp = self.router.get_greeting_response()
            latencia_ms = round((time.perf_counter() - t_inicio) * 1000, 2)
            resp["metadatos"] = {
                "latencia_total_ms": latencia_ms,
                "modelo": settings.GEMINI_MODEL
            }
            return resp

        # 2. RUTA: Extracción Estructurada JSON (LoRA Adapter)
        if ruta == "STRUCTURED_EXTRACT":
            dictamen = self.lora_adapter.extract(query)
            latencia_ms = round((time.perf_counter() - t_inicio) * 1000, 2)
            return {
                "respuesta": json.dumps(dictamen, ensure_ascii=False, indent=2),
                "dictamen_json": dictamen,
                "ruta": "STRUCTURED_EXTRACT",
                "fuentes": ["Adaptador_Estructurado_LoRA", settings.GEMINI_MODEL],
                "confianza": 0.98,
                "metadatos": {
                    "latencia_total_ms": latencia_ms,
                    "modelo": settings.GEMINI_MODEL,
                    "tipo_salida": "application/json"
                }
            }

        # 3. RUTA: Búsqueda RAG en el documento o ley activa
        fragmentos = self.rag_engine.search(query)
        fuentes_web = []

        # Control de abstención para consultas evidentemente ajenas al ámbito jurídico
        terminos_legales = ["ley", "artículo", "articulo", "código", "codigo", "derecho", "contrato", 
                            "delito", "trabajo", "lft", "penal", "norma", "reforma", "dof", "cláusula",
                            "clausula", "aviso", "penalización", "penalizacion", "rescisión", "rescision",
                            "arco", "confidencial", "nda", "honorarios", "aguinaldo", "vacaciones"]
        es_tema_legal = any(kw in query.lower() for kw in terminos_legales)
        max_confianza = max([f.get("confianza", 0.0) for f in fragmentos], default=0.0)

        if not es_tema_legal and max_confianza < 0.48:
            latencia_ms = round((time.perf_counter() - t_inicio) * 1000, 2)
            return {
                "respuesta": "No cuento con información oficial ni disposiciones jurídicas sobre este tema en el acervo legal activo. Mi especialidad es el cumplimiento normativo, contratos y legislación aplicable.",
                "ruta": "RAG_OUT_OF_DOMAIN",
                "fuentes": [],
                "confianza": 0.0,
                "fuentes_web": [],
                "metadatos": {
                    "latencia_total_ms": latencia_ms,
                    "modelo": settings.GEMINI_MODEL
                }
            }

        # Si se solicita búsqueda en internet o el RAG local tiene confianza moderada
        if enable_web_search or not fragmentos:
            fuentes_web = self.web_searcher.search_legal_context(query)

        # Contexto acumulado
        if fragmentos:
            contexto_combinado = "\n\n".join([f"[{f['titulo']}]\n{f['texto']}" for f in fragmentos])
            fuentes_lista = [f["titulo"] for f in fragmentos]
            confianza_max = max(f["confianza"] for f in fragmentos)
        else:
            contexto_combinado = "No se encontraron cláusulas locales exactas para esta consulta específica en el expediente activo."
            fuentes_lista = []
            confianza_max = 0.50 if fuentes_web else 0.0

        if fuentes_web:
            for fw in fuentes_web:
                fuentes_lista.append(f"Web: {fw['titulo']}")

        # Inferencia con Gemini 3.8 Flash
        respuesta_modelo = self.gemini_client.generate_factual_response(
            pregunta=query,
            contexto_rag=contexto_combinado,
            fuentes_web=fuentes_web
        )

        latencia_ms = round((time.perf_counter() - t_inicio) * 1000, 2)

        return {
            "respuesta": respuesta_modelo,
            "ruta": "RAG_SEARCH_WITH_WEB" if fuentes_web else "RAG_SEARCH",
            "fuentes": fuentes_lista,
            "confianza": confianza_max,
            "fuentes_web": fuentes_web,
            "metadatos": {
                "latencia_total_ms": latencia_ms,
                "modelo": settings.GEMINI_MODEL,
                "corpus_activo": self.rag_engine.current_corpus_id,
                "documento_personalizado": self.rag_engine.active_custom_doc
            }
        }


# Instancia singleton para FastAPI y CLI
pipeline_legal = LegalAIPipeline()
