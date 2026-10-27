"""Punto de entrada de la aplicación del taller."""

import tkinter as tk
from tkinter import messagebox, ttk

import database
from ui.clientes import Clientes
from ui.documentos import Documentos
from ui.estilos import aplicar_estilos
from ui.gastos import Gastos
from ui.historial import Historial
from ui.inicio import Inicio
from ui.inventario import Inventario
from ui.nomina import Nomina
from ui.proveedores import Proveedores
from ui.servicios import Servicios
from ui.trabajadores import Trabajadores


class AplicacionTaller(tk.Tk):
    """Ventana raíz y coordinadora de pestañas y accesos rápidos."""

    def __init__(self) -> None:
        super().__init__()
        aplicar_estilos(self)
        self.title("Sistema de gestión del taller")
        self.geometry("1280x760")
        self.minsize(1200, 700)
        self.status_texto = tk.StringVar(value="Listo")

        contenedor = ttk.Frame(self, padding=8)
        contenedor.pack(fill="both", expand=True)
        self.pestanas = ttk.Notebook(contenedor)
        self.pestanas.pack(fill="both", expand=True)
        self.pantallas: dict[str, ttk.Frame] = {}

        pantallas = (
            ("Inicio", Inicio),
            ("Inventario", Inventario),
            ("Servicios", Servicios),
            ("Trabajadores", Trabajadores),
            ("Clientes", Clientes),
            ("Proveedores", Proveedores),
            ("Documentos", Documentos),
            ("Nómina", Nomina),
            ("Gastos", Gastos),
            ("Historial", Historial),
        )
        for nombre, clase in pantallas:
            pestaña = clase(self.pestanas, self.mostrar_estado)
            self.pestanas.add(pestaña, text=nombre)
            self.pantallas[nombre] = pestaña

        self.pestanas.bind("<<NotebookTabChanged>>", self._actualizar_pestana)

        ttk.Separator(self, orient="horizontal").pack(fill="x")
        ttk.Label(self, textvariable=self.status_texto, anchor="w", padding=(8, 4)).pack(
            fill="x"
        )

    def mostrar_estado(self, mensaje: str) -> None:
        self.status_texto.set(mensaje)

    def _actualizar_pestana(self, evento: tk.Event | None = None) -> None:
        """Refresca los datos de la pestaña cada vez que se abre."""
        if evento is not None and evento.widget is not self.pestanas:
            return
        seleccion = self.pestanas.select()
        if not seleccion:
            return
        pestaña = self.nametowidget(seleccion)
        actualizar = getattr(pestaña, "actualizar", None)
        if callable(actualizar):
            actualizar()

    def abrir_documento(self, tipo: str) -> None:
        """Navega a Documentos y abre el formulario del tipo solicitado."""
        pantalla = self.pantallas["Documentos"]
        self.pestanas.select(pantalla)
        abrir_nuevo = getattr(pantalla, "abrir_nuevo", None)
        if callable(abrir_nuevo):
            abrir_nuevo(tipo)

    def abrir_historial(self) -> None:
        self.pestanas.select(self.pantallas["Historial"])


def main() -> None:
    """Inicializa la base local y ejecuta el bucle de eventos de Tk."""
    try:
        database.inicializar_bd()
    except database.ErrorBaseDatos as error:
        messagebox.showerror("Error de inicio", str(error))
        return
    AplicacionTaller().mainloop()


if __name__ == "__main__":
    main()
