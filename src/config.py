"""
Módulo de Configuración Tipada del Sistema (Pydantic / python-dotenv).
Centraliza variables de entorno, claves de API y rutas de archivos.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Resolver ruta base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar archivo .env si existe
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()


class Settings:
    """Configuración del sistema Iuris AI."""

    # 1. Credenciales y Modelo de Google Gemini
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "tu_gemini_api_key_aqui").strip()
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()

    # 2. Configuración del Motor RAG y Documentos
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2").strip()
    RAG_SIMILARITY_THRESHOLD: float = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.35"))
    RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "3"))
    CORPUS_FILE_PATH: Path = BASE_DIR / "data" / "normativas_corporativas.txt"
    UPLOAD_DIR: Path = BASE_DIR / "data" / "uploads"

    # 3. Configuración del Servidor HTTP
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @property
    def is_gemini_configured(self) -> bool:
        """Verifica si la API Key de Gemini fue ingresada por el usuario."""
        invalid_keys = {"", "tu_gemini_api_key_aqui", "TU_API_KEY_AQUI", "none"}
        return bool(self.GEMINI_API_KEY and self.GEMINI_API_KEY.lower() not in invalid_keys)


# Instancia singleton accesible en todo el proyecto
settings = Settings()

# Asegurar que exista el directorio de subidas
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
