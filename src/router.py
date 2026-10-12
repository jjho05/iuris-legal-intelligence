"""
Enrutador Inteligente de Intenciones (ModelRouter).
Clasifica en milisegundos las peticiones para optimizar latencia, costos de API y seguridad.
"""

from typing import Dict, Any


class ModelRouter:
    """Clasificador heurístico y semántico de intenciones para Iuris AI."""

    def __init__(self):
        self.greetings = {
            "hola", "buenos dias", "buenas tardes", "buenas noches",
            "que tal", "saludos", "buen dia", "hey", "hello"
        }
        self.extraction_keywords = {
            "json", "extraer", "clasificar", "ficha", "estructura",
            "resumen estructurado", "dictamen", "formato json", "extrae"
        }

    def route(self, query: str) -> str:
        """
        Determina la ruta de ejecución óptima para la consulta:
        - DIRECT_GREETING: Atajo de respuesta inmediata (< 1ms).
        - STRUCTURED_EXTRACT: Requerimiento de salida estructurada tipada JSON.
        - RAG_SEARCH: Consulta fáctica hacia la base documental jurídica.
        """
        cleaned = query.strip().lower()

        # 1. Atajo ultrarrápido para saludos directos de cortesía
        palabras = cleaned.split()
        if len(palabras) <= 4:
            for g in self.greetings:
                if cleaned == g or cleaned.startswith(g):
                    return "DIRECT_GREETING"

        # 2. Detección de peticiones de extracción estructurada JSON
        if any(keyword in cleaned for keyword in self.extraction_keywords):
            return "STRUCTURED_EXTRACT"

        # 3. Flujo principal: Consulta fáctica a ser contrastada con el motor RAG
        return "RAG_SEARCH"

    def get_greeting_response(self) -> Dict[str, Any]:
        """Devuelve respuesta corporativa estandarizada para saludos."""
        return {
            "respuesta": (
                "Hola, un gusto saludarte. Soy Iuris Legal Assistant, tu asesor pericial en "
                "cumplimiento normativo, contratos y legislación aplicable. ¿En qué asunto jurídico, "
                "política o cláusula contractual requieres orientación hoy?"
            ),
            "ruta": "DIRECT_GREETING",
            "fuentes": [],
            "confianza": 1.0,
            "metadatos": {
                "latencia_enrutamiento_ms": 0.5,
                "modelo_utilizado": "FastPath-Heuristic-Router"
            }
        }
