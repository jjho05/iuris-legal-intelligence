"""
Módulo de Búsqueda y Grounding Web de Leyes Vigentes (web_search.py).
Permite consultar internet para leyes, artículos del DOF, jurisprudencia y reformas en tiempo real.
"""

import urllib.parse
import urllib.request
import json
import re
from typing import List, Dict, Any, Optional


class LegalWebSearcher:
    """Buscador web especializado en fuentes jurídicas y legislación vigente."""

    def __init__(self, timeout: int = 6):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 IurisLegalBot/2.0"
        }

    def search_legal_context(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """
        Busca en la web fuentes oficiales sobre leyes, decretos y jurisprudencias.
        Utiliza el motor de DuckDuckGo API / HTML para obtener fragmentos fácticos sin requerir API keys de terceros.
        """
        # Refinar consulta para priorizar fuentes legales confiables
        legal_query = f"{query} ley mexico diario oficial diputados justo"
        encoded = urllib.parse.quote(legal_query)

        # 1. Intentar consulta a DuckDuckGo Instant Answer API
        try:
            api_url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
            req = urllib.request.Request(api_url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                results = []

                if data.get("AbstractText"):
                    results.append({
                        "titulo": data.get("Heading", "Legislación / Concepto Oficial"),
                        "snippet": data.get("AbstractText"),
                        "url": data.get("AbstractURL", "https://diputados.gob.mx/LeyesBiblio/")
                    })

                for topic in data.get("RelatedTopics", [])[:max_results]:
                    if "Text" in topic:
                        results.append({
                            "titulo": topic.get("FirstURL", "").split("/")[-1].replace("_", " ").title() or "Fuente Jurídica",
                            "snippet": topic["Text"],
                            "url": topic.get("FirstURL", "https://diputados.gob.mx/")
                        })

                if results:
                    return results[:max_results]
        except Exception as e:
            pass

        # 2. Respaldo determinista curado de legislación mexicana esencial si falla la red
        return self._fallback_legal_search(query)

    def _fallback_legal_search(self, query: str) -> List[Dict[str, Any]]:
        """Catálogo de referencia de las leyes federales más recurrentes."""
        q = query.lower()
        results = []

        if "trabajo" in q or "lft" in q or "vacaci" in q or "despido" in q or "salario" in q:
            results.append({
                "titulo": "Ley Federal del Trabajo (LFT) - Reforma de Vacaciones Dignas y Jornadas",
                "snippet": "Artículo 76 LFT: Las personas trabajadoras que tengan más de un año de servicios disfrutarán de un periodo anual de vacaciones pagadas que en ningún caso podrá ser inferior a doce días laborables, aumentando en dos días por cada año subsecuente hasta llegar a veinte.",
                "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LFT.pdf"
            })
            results.append({
                "titulo": "LFT - Artículo 47: Causas de rescisión de la relación de trabajo sin responsabilidad para el patrón",
                "snippet": "El patrón podrá rescindir la relación laboral por faltas de probidad, violencia, injurias, daño intencional a las instalaciones o más de tres faltas de asistencia en un período de treinta días sin causa justificada.",
                "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LFT.pdf"
            })

        elif "penal" in q or "delito" in q or "prisi" in q or "fraude" in q or "homicidio" in q:
            results.append({
                "titulo": "Código Penal Federal (CPF) - Tipificación y Sanciones",
                "snippet": "Artículo 386 CPF: Comete el delito de fraude el que engañando a uno o aprovechándose del error en que éste se halla se hace ilícitamente de alguna cosa o alcanza un lucro indebido. Las sanciones varían según el monto de lo defraudado.",
                "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/CPF.pdf"
            })

        elif "comercio" in q or "mercantil" in q or "pagare" in q or "sociedad" in q:
            results.append({
                "titulo": "Código de Comercio & Ley General de Sociedades Mercantiles",
                "snippet": "Artículo 1054 del Código de Comercio: Los juicios mercantiles se regirán por las disposiciones de este Código y, en su defecto, por el Código Federal de Procedimientos Civiles y la ley de procedimientos local respectiva.",
                "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/CCo.pdf"
            })

        else:
            results.append({
                "titulo": "Cámara de Diputados - Portal de Leyes Federales de México",
                "snippet": "Repositorio general de leyes federales vigentes, códigos nacionales y reformas constitucionales publicadas en el Diario Oficial de la Federación.",
                "url": "https://www.diputados.gob.mx/LeyesBiblio/"
            })

        return results


# Instancia singleton para uso en el pipeline
web_searcher = LegalWebSearcher()
