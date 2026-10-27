"""Generación de facturas, cotizaciones y órdenes en formato PDF."""

from html import escape
from pathlib import Path
import sys
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.doctemplate import LayoutError

from utils.helpers import fecha_pantalla, formatear_moneda


_DIRECTORIO_SALIDA = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent.parent
)
CARPETA_PDFS = _DIRECTORIO_SALIDA / "pdfs"


class ErrorGeneracionPDF(Exception):
    """Error al construir el archivo PDF."""


def _texto(valor: Any) -> str:
    return escape(str(valor or "")).replace("\n", "<br/>")


def _formato_fecha(valor: str | None) -> str:
    if not valor:
        return ""
    return fecha_pantalla(valor)


def _nombre_archivo(documento: dict[str, Any]) -> str:
    """Construye el nombre estable tipo_numero.pdf."""
    tipo = str(documento.get("tipo", "documento")).lower().replace(" ", "_")
    numero = documento.get("numero", documento.get("id", "sin_numero"))
    return f"{tipo}_{numero}.pdf"


def _estilos() -> dict[str, ParagraphStyle]:
    """Define una sola vez los estilos compartidos por todos los reportes."""
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "TituloTaller", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=16, leading=20, alignment=TA_CENTER, spaceAfter=10,
        ),
        "encabezado": ParagraphStyle(
            "EncabezadoTaller", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=11, leading=14, spaceAfter=4,
        ),
        "normal": ParagraphStyle(
            "NormalTaller", parent=base["Normal"], fontName="Helvetica",
            fontSize=9, leading=12,
        ),
        "celda": ParagraphStyle(
            "CeldaTaller", parent=base["Normal"], fontName="Helvetica",
            fontSize=8, leading=10,
        ),
        "celda_derecha": ParagraphStyle(
            "CeldaDerechaTaller", parent=base["Normal"], fontName="Helvetica",
            fontSize=8, leading=10, alignment=TA_RIGHT,
        ),
    }


def _parrafo(valor: Any, estilo: ParagraphStyle) -> Paragraph:
    return Paragraph(_texto(valor), estilo)


def _tabla_detalle(
    lineas: list[dict[str, Any]], estilos: dict[str, ParagraphStyle]
) -> Table:
    """Crea la tabla comercial sin exponer porcentajes ni pagos internos."""
    datos = [[
        _parrafo("Descripción", estilos["encabezado"]),
        _parrafo("Cantidad", estilos["encabezado"]),
        _parrafo("Precio", estilos["encabezado"]),
        _parrafo("Subtotal", estilos["encabezado"]),
    ]]
    for linea in lineas:
        datos.append([
            _parrafo(linea.get("descripcion") or linea.get("nombre") or "", estilos["celda"]),
            _parrafo(linea.get("cantidad", ""), estilos["celda_derecha"]),
            _parrafo(formatear_moneda(linea.get("precio_unitario", 0)), estilos["celda_derecha"]),
            _parrafo(
                formatear_moneda(linea.get("subtotal", 0)), estilos["celda_derecha"]
            ),
        ])
    tabla = Table(datos, colWidths=(8.6 * cm, 2.1 * cm, 3.1 * cm, 3.2 * cm), repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9eef3")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9aa5b1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return tabla


def _generar(
    documento: dict[str, Any],
    detalle: list[dict[str, Any]],
    titulo: str,
    elementos_adicionales: list[Any] | None = None,
    destino: str | Path | None = None,
    nombre_taller: str = "TALLER",
) -> Path:
    """Compone la página carta común y escribe el PDF en el destino indicado."""
    ruta = Path(destino) if destino else CARPETA_PDFS / _nombre_archivo(documento)
    estilos = _estilos()
    contenido: list[Any] = [
        _parrafo(nombre_taller, estilos["titulo"]),
        _parrafo(titulo, estilos["encabezado"]),
        Paragraph(
            f"<b>Número:</b> {_texto(documento.get('numero'))} &nbsp;&nbsp; "
            f"<b>Fecha:</b> {_texto(_formato_fecha(documento.get('fecha_emision')))}",
            estilos["normal"],
        ),
        Paragraph(
            f"<b>Cliente:</b> {_texto(documento.get('cliente'))}", estilos["normal"]
        ),
        Spacer(1, 0.35 * cm),
    ]
    if elementos_adicionales:
        contenido.extend(elementos_adicionales)
        contenido.append(Spacer(1, 0.25 * cm))
    contenido.extend([
        _tabla_detalle(detalle, estilos),
        Spacer(1, 0.35 * cm),
    ])
    totales = Table(
        [[Paragraph("<b>Total</b>", estilos["normal"]),
          Paragraph(
              f"<b>{formatear_moneda(documento.get('total', 0))}</b>",
              estilos["celda_derecha"],
          )]],
        colWidths=(13.8 * cm, 3.2 * cm),
    )
    totales.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, -1), 0.8, colors.black),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    contenido.append(totales)
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        plantilla = SimpleDocTemplate(
            str(ruta), pagesize=letter, rightMargin=2 * cm, leftMargin=2 * cm,
            topMargin=2 * cm, bottomMargin=2 * cm, title=titulo,
            author=nombre_taller,
        )
        plantilla.build(contenido)
    except (OSError, ValueError, TypeError, LayoutError) as error:
        raise ErrorGeneracionPDF(f"No se pudo generar el PDF: {error}") from error
    return ruta


def generar_factura(
    documento: dict[str, Any], detalle: list[dict[str, Any]],
    destino: str | Path | None = None, nombre_taller: str = "TALLER",
) -> Path:
    """Genera la factura con la falla reportada y las notas del documento."""
    estilos = _estilos()
    adicionales = [
        _campo(etiqueta, documento.get(campo), estilos)
        for etiqueta, campo in (
            ("Requerimiento / falla reportada", "falla_reportada"),
            ("Notas", "notas"),
        )
        if documento.get(campo)
    ]
    return _generar(
        documento, detalle, "FACTURA", adicionales,
        destino=destino, nombre_taller=nombre_taller,
    )


def generar_cotizacion(
    documento: dict[str, Any], detalle: list[dict[str, Any]],
    destino: str | Path | None = None, nombre_taller: str = "TALLER",
) -> Path:
    """Genera la cotización de cliente."""
    return _generar(
        documento, detalle, "COTIZACIÓN", destino=destino, nombre_taller=nombre_taller
    )


def _campo(etiqueta: str, valor: Any, estilos: dict[str, ParagraphStyle]) -> Paragraph:
    return Paragraph(f"<b>{escape(etiqueta)}:</b> {_texto(valor)}", estilos["normal"])


def generar_orden_servicio(
    documento: dict[str, Any], detalle: list[dict[str, Any]],
    destino: str | Path | None = None, nombre_taller: str = "TALLER",
) -> Path:
    """Genera la OS con los campos operativos del vehículo o equipo."""
    estilos = _estilos()
    adicionales = [
        _campo("Inicio", _formato_fecha(documento.get("fecha_inicio")), estilos),
        _campo("Entrega", _formato_fecha(documento.get("fecha_entrega")), estilos),
        _campo("Equipo", documento.get("equipo"), estilos),
        _campo("Placa", documento.get("placa"), estilos),
        _campo("Serial / OT", documento.get("serial_ot"), estilos),
        _campo("Tiempo estimado", documento.get("tiempo_estimado"), estilos),
        _campo("Falla reportada", documento.get("falla_reportada"), estilos),
        _campo("Causa de falla", documento.get("causa_falla"), estilos),
        _campo("Trabajos ejecutados", documento.get("trabajos_ejecutados"), estilos),
        _campo("Recomendaciones", documento.get("recomendaciones"), estilos),
    ]
    return _generar(
        documento, detalle, "ORDEN DE SERVICIO", adicionales, destino, nombre_taller
    )


def generar_orden_trabajo(
    documento: dict[str, Any], detalle: list[dict[str, Any]],
    destino: str | Path | None = None, nombre_taller: str = "TALLER",
) -> Path:
    """Genera la OT e identifica servicios y trabajadores asignados."""
    estilos = _estilos()
    trabajadores: list[str] = []
    for linea in detalle:
        for asignacion in linea.get("trabajadores", []):
            nombre = asignacion.get("trabajador")
            if nombre and nombre not in trabajadores:
                trabajadores.append(nombre)
    servicios = [
        str(linea.get("descripcion") or linea.get("nombre") or "")
        for linea in detalle if linea.get("item_tipo") == "servicio"
    ]
    adicionales = [
        _campo("Requerimiento", documento.get("falla_reportada"), estilos),
        _campo("Trabajador", ", ".join(trabajadores), estilos),
        _campo("Servicios a realizar", ", ".join(servicios), estilos),
    ]
    return _generar(
        documento, detalle, "ORDEN DE TRABAJO", adicionales, destino, nombre_taller
    )


def generar_pdf(
    documento: dict[str, Any],
    detalle: list[dict[str, Any]] | None = None,
    destino: str | Path | None = None,
    nombre_taller: str = "TALLER",
) -> Path:
    """Selecciona el generador a partir del tipo guardado en el documento."""
    filas = detalle if detalle is not None else documento.get("detalle", [])
    funciones = {
        "factura": generar_factura,
        "cotizacion": generar_cotizacion,
        "orden_servicio": generar_orden_servicio,
        "orden_trabajo": generar_orden_trabajo,
    }
    funcion = funciones.get(str(documento.get("tipo", "")))
    if funcion is None:
        raise ErrorGeneracionPDF("Tipo de documento no reconocido.")
    return funcion(documento, filas, destino=destino, nombre_taller=nombre_taller)


def generar_desprendible_pdf(
    desprendible: dict[str, Any],
    destino: str | Path | None = None,
    nombre_taller: str = "TALLER",
) -> Path:
    """Genera el comprobante de pago de comisiones de un trabajador."""
    numero = desprendible.get("numero", desprendible.get("id", "sin_numero"))
    trabajador_id = desprendible.get("trabajador_id", "sin_trabajador")
    desprendible_id = desprendible.get("id", numero)
    ruta = (
        Path(destino)
        if destino
        else CARPETA_PDFS
        / f"desprendible_{trabajador_id}_{numero}_{desprendible_id}.pdf"
    )
    estilos = _estilos()
    inicio = _formato_fecha(desprendible.get("periodo_inicio")) or "Todas las pendientes"
    fin = _formato_fecha(desprendible.get("periodo_fin")) or "Todas las pendientes"
    contenido: list[Any] = [
        _parrafo(nombre_taller, estilos["titulo"]),
        _parrafo("DESPRENDIBLE DE PAGO", estilos["titulo"]),
        _campo("Número", numero, estilos),
        _campo("Trabajador", desprendible.get("trabajador"), estilos),
        _campo("Cédula", desprendible.get("cedula"), estilos),
        _campo("Cargo", desprendible.get("cargo"), estilos),
        _campo("Período", f"{inicio} a {fin}", estilos),
        _campo("Fecha de emisión", _formato_fecha(desprendible.get("fecha_emision")), estilos),
        Spacer(1, 0.4 * cm),
    ]
    filas = [[
        _parrafo("Fecha", estilos["encabezado"]),
        _parrafo("Servicio", estilos["encabezado"]),
        _parrafo("%", estilos["encabezado"]),
        _parrafo("Monto", estilos["encabezado"]),
    ]]
    for comision in desprendible.get("comisiones", []):
        # El porcentaje se muestra en el recibo interno de nómina, no en los
        # documentos comerciales que se entregan al cliente.
        filas.append([
            _parrafo(_formato_fecha(comision.get("fecha_generacion")), estilos["celda"]),
            _parrafo(comision.get("servicio") or "Servicio", estilos["celda"]),
            _parrafo(f'{float(comision.get("porcentaje") or 0):g}%', estilos["celda_derecha"]),
            _parrafo(formatear_moneda(comision.get("monto")), estilos["celda_derecha"]),
        ])
    tabla = Table(
        filas, colWidths=(3.1 * cm, 8.2 * cm, 2.5 * cm, 3.2 * cm), repeatRows=1
    )
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9eef3")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9aa5b1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    contenido.extend([tabla, Spacer(1, 0.5 * cm)])
    total = Table(
        [[Paragraph("<b>TOTAL A PAGAR</b>", estilos["encabezado"]),
          Paragraph(
              f"<b>{formatear_moneda(desprendible.get('total', 0))}</b>",
              ParagraphStyle(
                       "TotalDesprendible", parent=estilos["celda_derecha"],
                       fontName="Helvetica-Bold", fontSize=14, leading=18,
              ),
          )]],
        colWidths=(12.5 * cm, 4.5 * cm),
    )
    total.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, -1), 1, colors.black),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    contenido.append(total)
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        SimpleDocTemplate(
            str(ruta), pagesize=letter, rightMargin=2 * cm, leftMargin=2 * cm,
            topMargin=2 * cm, bottomMargin=2 * cm,
            title="DESPRENDIBLE DE PAGO", author=nombre_taller,
        ).build(contenido)
    except (OSError, ValueError, TypeError, LayoutError) as error:
        raise ErrorGeneracionPDF(f"No se pudo generar el desprendible PDF: {error}") from error
    return ruta
