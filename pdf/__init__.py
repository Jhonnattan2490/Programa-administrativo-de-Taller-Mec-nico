"""Generación de documentos PDF."""

from pdf.generador_pdf import (
    ErrorGeneracionPDF,
    generar_factura,
    generar_orden_servicio,
    generar_orden_trabajo,
    generar_pdf,
    generar_cotizacion,
    generar_desprendible_pdf,
)

__all__ = [
    "ErrorGeneracionPDF",
    "generar_pdf",
    "generar_factura",
    "generar_cotizacion",
    "generar_orden_servicio",
    "generar_orden_trabajo",
    "generar_desprendible_pdf",
]
