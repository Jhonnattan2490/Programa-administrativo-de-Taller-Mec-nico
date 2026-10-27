"""Panel de resumen y accesos rápidos."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable

import database
from utils.helpers import formatear_moneda


class Inicio(ttk.Frame):
    """Dashboard compacto conectado a los indicadores agregados de SQLite."""

    def __init__(self, master: tk.Misc, estado: Callable[[str], None]) -> None:
        super().__init__(master, padding=18)
        self.estado = estado
        ttk.Label(
            self, text="Resumen del taller", font=("TkDefaultFont", 20, "bold")
        ).pack(anchor="w", pady=(0, 14))
        tarjetas = ttk.Frame(self)
        tarjetas.pack(fill="both", expand=True)
        tarjetas.columnconfigure((0, 1), weight=1, uniform="tarjeta")
        tarjetas.rowconfigure((0, 1), weight=1, uniform="tarjeta")

        self.valor_stock, self.detalle_stock = self._crear_tarjeta(
            tarjetas, 0, 0, "Productos con stock bajo", "productos"
        )
        self.valor_hoy, _ = self._crear_tarjeta(
            tarjetas, 0, 1, "Ventas del día", "Total facturado hoy"
        )
        self.valor_comisiones, _ = self._crear_tarjeta(
            tarjetas, 1, 0, "Comisiones pendientes de pago", "Saldo total a trabajadores"
        )
        self.valor_mes, _ = self._crear_tarjeta(
            tarjetas, 1, 1, "Facturado este mes", "Facturas emitidas y pagadas"
        )

        accesos = ttk.Frame(self, padding=(0, 12, 0, 0))
        accesos.pack(fill="x")
        ttk.Label(accesos, text="Accesos rápidos", font=("TkDefaultFont", 12, "bold")).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(
            accesos, text="Nueva Factura",
            command=lambda: self._abrir_documento("factura"),
        ).pack(side="left", padx=4)
        ttk.Button(
            accesos, text="Nueva OS",
            command=lambda: self._abrir_documento("orden_servicio"),
        ).pack(side="left", padx=4)
        ttk.Button(
            accesos, text="Ver Historial", command=self._abrir_historial
        ).pack(side="left", padx=4)
        self.actualizar()

    @staticmethod
    def _crear_tarjeta(
        contenedor: ttk.Frame, fila: int, columna: int,
        titulo: str, subtitulo: str,
    ) -> tuple[ttk.Label, ttk.Label]:
        tarjeta = ttk.LabelFrame(contenedor, text=titulo, padding=14)
        tarjeta.grid(row=fila, column=columna, sticky="nsew", padx=6, pady=6)
        valor = ttk.Label(tarjeta, text="—", font=("TkDefaultFont", 22, "bold"))
        valor.pack(anchor="w", pady=(3, 4))
        detalle = ttk.Label(tarjeta, text=subtitulo, justify="left")
        detalle.pack(anchor="w")
        return valor, detalle

    def actualizar(self) -> None:
        """Actualiza cada tarjeta con una sola consulta agregada del backend."""
        try:
            resumen: dict[str, Any] = database.resumen_dashboard()
            productos = resumen["stock_bajo"]
            self.valor_stock.configure(text=str(resumen["total_stock_bajo"]))
            if productos:
                lineas = [
                    f'{p["nombre"]}: {p["stock"]} (mín. {p["stock_minimo"]})'
                    for p in productos
                ]
                self.detalle_stock.configure(text="\n".join(lineas))
            else:
                self.detalle_stock.configure(text="Sin productos bajo el mínimo")
            self.valor_hoy.configure(text=formatear_moneda(resumen["ventas_hoy"]))
            self.valor_comisiones.configure(
                text=formatear_moneda(resumen["comisiones_pendientes"])
            )
            self.valor_mes.configure(text=formatear_moneda(resumen["facturado_mes"]))
        except database.ErrorBaseDatos as error:
            messagebox.showerror("Error del dashboard", str(error))

    def _abrir_documento(self, tipo: str) -> None:
        """Solicita a la ventana principal abrir el formulario documental."""
        ventana = self.winfo_toplevel()
        accion = getattr(ventana, "abrir_documento", None)
        if callable(accion):
            accion(tipo)
        else:
            self.estado("No se pudo abrir la pestaña de documentos.")

    def _abrir_historial(self) -> None:
        ventana = self.winfo_toplevel()
        accion = getattr(ventana, "abrir_historial", None)
        if callable(accion):
            accion()
        else:
            self.estado("No se pudo abrir la pestaña de historial.")
