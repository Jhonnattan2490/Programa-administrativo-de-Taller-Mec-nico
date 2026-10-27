"""Funciones de presentación y formato."""

from datetime import date, datetime


def formatear_moneda(valor: float | int | str | None) -> str:
    """Muestra un monto con separador de miles en formato local."""
    numero = float(valor or 0)
    return "$" + f"{numero:,.0f}".replace(",", ".")


def fecha_hoy_iso() -> str:
    """Retorna la fecha actual como texto ISO para SQLite."""
    return date.today().isoformat()


def fecha_pantalla(fecha_iso: str | None) -> str:
    """Convierte fecha ISO a dd/mm/aaaa sin fallar ante datos heredados."""
    if not fecha_iso:
        return ""
    try:
        return datetime.strptime(fecha_iso, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return fecha_iso


def fecha_iso(fecha_texto: str) -> str:
    """Valida y convierte una fecha dd/mm/aaaa a formato ISO."""
    return datetime.strptime(fecha_texto.strip(), "%d/%m/%Y").date().isoformat()


def siguiente_consecutivo(actual: int | None) -> int:
    """Calcula el siguiente consecutivo a partir del último número guardado."""
    return int(actual or 0) + 1
