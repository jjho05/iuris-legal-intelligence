"""
Pruebas de Ingestión y Conversión de Documentos a Markdown (test_document_processor.py).
Valida que archivos Word DOCX, PDF y texto se conviertan a Markdown estructurado sin errores.
"""

import io
import pytest
from docx import Document
from src.document_processor import document_processor


def test_docx_to_markdown_conversion():
    """Crea un documento Word en memoria con párrafos y tablas y valida su Markdown."""
    doc = Document()
    doc.add_heading("Contrato de Prestación de Servicios de Software", level=1)
    doc.add_paragraph("Este contrato se celebra entre Empresa Alfa y Proveedor Beta.")
    
    # Agregar Cláusula
    doc.add_heading("Cláusula Primera: Objeto del Contrato", level=2)
    doc.add_paragraph("El proveedor entregará los módulos acordados en un plazo de 60 días naturales.")

    # Agregar Tabla
    table = doc.add_table(rows=2, cols=2)
    table.rows[0].cells[0].text = "Hito"
    table.rows[0].cells[1].text = "Monto (USD)"
    table.rows[1].cells[0].text = "Entrega Fase 1"
    table.rows[1].cells[1].text = "10,000"

    # Guardar en memoria de bytes
    f_bytes = io.BytesIO()
    doc.save(f_bytes)
    f_bytes.seek(0)

    # Procesar
    resultado = document_processor.process_file(f_bytes.read(), "contrato_demo.docx")

    assert resultado["tipo_documento"] == "Word DOCX"
    assert resultado["secciones_detectadas"] >= 1
    assert "Contrato de Prestación de Servicios de Software" in resultado["markdown"]
    assert "Cláusula Primera" in resultado["markdown"]
    assert "| Hito | Monto (USD) |" in resultado["markdown"]
    assert resultado["palabras"] > 20


def test_txt_to_markdown_conversion():
    """Valida la conversión de texto plano con artículos a Markdown estructurado."""
    texto = """Artículo 1: Objeto
Las partes convienen la prestación de servicios legales.

Artículo 2: Honorarios
Los honorarios profesionales ascenderán a 5,000 USD mensuales."""

    resultado = document_processor.process_file(texto.encode("utf-8"), "estatuto.txt")
    assert resultado["tipo_documento"] == "Texto Plano / Markdown"
    assert resultado["secciones_detectadas"] >= 1
    assert "Artículo 1" in resultado["markdown"]
