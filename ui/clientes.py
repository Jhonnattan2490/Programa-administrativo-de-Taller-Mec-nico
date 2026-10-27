"""Catálogo de clientes."""

from ui.personas import CatalogoPersonas


class Clientes(CatalogoPersonas):
    """Catálogo de clientes conectado al CRUD de clientes."""

    entidad = "clientes"
    titulo = "Cliente"
