"""Catálogo de proveedores."""

from ui.personas import CatalogoPersonas


class Proveedores(CatalogoPersonas):
    """Catálogo de proveedores conectado al CRUD de proveedores."""

    entidad = "proveedores"
    titulo = "Proveedor"
