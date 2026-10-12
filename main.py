"""
Punto de Entrada Principal (main.py).
Permite arrancar el servidor FastAPI o probar el sistema en modo consola interactiva.
"""

import sys
import argparse
import uvicorn
from src.config import settings
from src.pipeline import pipeline_legal


def ejecutar_modo_consola():
    """Ejecuta un bucle interactivo en terminal para pruebas rápidas de ingeniería."""
    print("=" * 70)
    print(" IURIS LEGAL INTELLIGENCE — ASISTENTE JURÍDICO & CONTRATOS (MODO CONSOLA)")
    print("=" * 70)
    print(f"- Modelo Configurado: {settings.GEMINI_MODEL}")
    print(f"- Gemini API: {'CONECTADA' if settings.is_gemini_configured else 'MODO SIMULACIÓN (Configura GEMINI_API_KEY en .env)'}")
    print(f"- Cláusulas Indexadas: {len(pipeline_legal.rag_engine.documentos)}")
    print(f"- Umbral RAG: {settings.RAG_SIMILARITY_THRESHOLD}")
    print("\nEscribe tu pregunta o escribe 'salir' para terminar.\n")

    while True:
        try:
            pregunta = input("\n[Usuario] >> ").strip()
            if not pregunta:
                continue
            if pregunta.lower() in {"salir", "exit", "quit"}:
                print("\nCerrando sesión de Iuris Legal Intelligence. Hasta pronto.")
                break

            resultado = pipeline_legal.procesar_consulta(pregunta)
            print("\n[Iuris Legal Intelligence]:")
            print(resultado["respuesta"])
            print("-" * 70)
            print(f"Ruta: {resultado['ruta']} | Confianza: {resultado.get('confianza', 0.0)} | Latencia: {resultado['metadatos'].get('latencia_total_ms', 0)} ms")
            if resultado.get("fuentes"):
                print(f"Fuentes: {', '.join(resultado['fuentes'])}")
        except KeyboardInterrupt:
            print("\nOperación cancelada por el usuario.")
            break
        except Exception as e:
            print(f"\n[Error]: {e}")


def arrancar_servidor():
    """Inicia el servidor web FastAPI con Uvicorn."""
    print(f"Iniciando servidor de Iuris Legal Intelligence en http://{settings.API_HOST}:{settings.API_PORT}")
    uvicorn.run(
        "src.api_server:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=(settings.ENVIRONMENT == "development")
    )


def main():
    parser = argparse.ArgumentParser(description="Iuris Legal Intelligence — Sistema LegalTech")
    parser.add_argument("--cli", action="store_true", help="Inicia en modo consola interactiva de prueba")
    parser.add_argument("--port", type=int, default=settings.API_PORT, help="Puerto para el servidor HTTP")
    args = parser.parse_args()

    if args.cli:
        ejecutar_modo_consola()
    else:
        if args.port != settings.API_PORT:
            settings.API_PORT = args.port
        arrancar_servidor()


if __name__ == "__main__":
    main()
