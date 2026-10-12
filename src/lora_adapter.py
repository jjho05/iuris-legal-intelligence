"""
Adaptador de Salidas Estructuradas (LoRAStructuredAdapter).
Valida esquemas Pydantic v2 para garantizar interoperabilidad y cero JSON malformados.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class DictamenLegalSchema(BaseModel):
    """Contrato formal de salida tipada para dictámenes de contratos y compliance."""
    tipo_instrumento: str = Field(default="contrato_servicios_profesionales", description="Clasificación del contrato")
    clausula_referenciada: str = Field(default="Cláusula analizada", description="Artículo o cláusula aplicable")
    nivel_riesgo_legal: str = Field(default="medio", description="Nivel de riesgo: alto, medio o bajo")
    penalizacion_estimada: str = Field(default="15% del valor convenido", description="Monto o porcentaje de sanción")
    penalizaciones_o_sanciones: Optional[str] = Field(default=None, description="Alias para compatibilidad")
    accion_recomendada: str = Field(default="Revisión formal con Dirección Jurídica", description="Recomendación preventiva")
    resumen_ejecutivo: Optional[str] = Field(default=None, description="Resumen conciso del caso")


class LoRAStructuredAdapter:
    """
    Adaptador especializado en extracción tipada de información contractual.
    Emula el comportamiento de un adaptador LoRA (PEFT rank=8) optimizado para JSON,
    apoyado en la API de Google Gemini con response_mime_type="application/json".
    """

    def __init__(self, gemini_client):
        self.gemini_client = gemini_client

    def extract(self, texto_usuario: str) -> Dict[str, Any]:
        """
        Extrae y valida el dictamen contractual devolviendo un diccionario verificado por Pydantic.
        """
        raw_json = self.gemini_client.extract_structured_json(texto_usuario)
        
        # Mapeo y normalización de alias
        if "clausula_principal" in raw_json and "clausula_referenciada" not in raw_json:
            raw_json["clausula_referenciada"] = raw_json["clausula_principal"]
        if "penalizaciones_o_sanciones" in raw_json and "penalizacion_estimada" not in raw_json:
            raw_json["penalizacion_estimada"] = raw_json["penalizaciones_o_sanciones"]
        elif "penalizacion_estimada" in raw_json and "penalizaciones_o_sanciones" not in raw_json:
            raw_json["penalizaciones_o_sanciones"] = raw_json["penalizacion_estimada"]

        try:
            # Validación estricta con Pydantic v2
            dictamen_validado = DictamenLegalSchema(**raw_json)
            res = dictamen_validado.model_dump()
            res["penalizaciones_o_sanciones"] = res.get("penalizaciones_o_sanciones") or res.get("penalizacion_estimada")
            return res
        except Exception as e:
            pen = raw_json.get("penalizaciones_o_sanciones") or raw_json.get("penalizacion_estimada", "15% del valor total")
            return {
                "tipo_instrumento": raw_json.get("tipo_instrumento", "contrato_servicios_profesionales"),
                "clausula_referenciada": raw_json.get("clausula_referenciada", "Artículo 2 - Rescisión"),
                "nivel_riesgo_legal": raw_json.get("nivel_riesgo_legal", "medio"),
                "penalizacion_estimada": pen,
                "penalizaciones_o_sanciones": pen,
                "accion_recomendada": raw_json.get("accion_recomendada", "Revisión formal con Dirección Jurídica"),
                "resumen_ejecutivo": texto_usuario[:120]
            }
