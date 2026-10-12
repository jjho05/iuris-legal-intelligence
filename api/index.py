"""
Entrypoint Serverless para Vercel (api/index.py).
Expone la aplicación FastAPI como una función serverless de Python.
"""

import sys
from pathlib import Path

# Agregar el directorio raíz del proyecto al sys.path para resolución de módulos
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Importar la aplicación FastAPI
from src.api_server import app

# Vercel espera la variable 'app'
__all__ = ["app"]
