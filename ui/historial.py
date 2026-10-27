"""Historial de movimientos y corte mensual."""

import tkinter as tk
from tkinter import messagebox, ttk
from datetime import date
from typing import Callable

import database
from utils.helpers import fecha_pantalla, formatear_moneda


class Historial(ttk.Frame):
    """Muestra movimientos mensuales, corte contable y obligaciones pendientes."""

    def __init__(self, master: tk.Misc, estado: Callable[[str], None]) -> None:
        super().__init__(master, padding=10)
        self.estado = estado
        self._crear_interfaz()
        self.actualizar()

    def _crear_interfaz(self) -> None:
        barra = ttk.Frame(self)
        barra.pack(fill="x", pady=(0, 8))
        hoy = date.today()
        ttk.Label(barra, text="Mes").pack(side="left", padx=(0, 4))
        self.mes = ttk.Combobox(
            barra, state="readonly", width=5,
            values=tuple(f"{numero:02d}" for numero in range(1, 13)),
        )
        self.mes.set(f"{hoy.month:02d}")
        self.mes.pack(side="left", padx=(0, 12))
        ttk.Label(barra, text="Año").pack(side="left", padx=(0, 4))
        self.anio = tk.Spinbox(barra, from_=2000, to=2100, width=7)
        self.anio.delete(0, "end")
        self.anio.insert(0, str(hoy.year))
        self.anio.pack(side="left", padx=(0, 8))
        ttk.Button(barra, text="Consultar corte", command=self.actualizar).pack(side="left")

        self.pestanas = ttk.Notebook(self)
        self.pestanas.pack(fill="both", expand=True)
        self.pestana_entradas = ttk.Frame(self.pestanas, padding=8)
        self.pestana_salidas = ttk.Frame(self.pestanas, padding=8)
        self.pestana_corte = ttk.Frame(self.pestanas, padding=8)
        self.pestana_pendientes = ttk.Frame(self.pestanas, padding=8)
        self.pestanas.add(self.pestana_entradas, text="Entradas")
        self.pestanas.add(self.pestana_salidas, text="Salidas")
        self.pestanas.add(self.pestana_corte, text="Corte mensual")
        self.pestanas.add(self.pestana_pendientes, text="Pendientes")

        self.tabla_entradas = self._crear_tabla(
            self.pestana_entradas,
            (("fecha", "Fecha", 110), ("numero", "N.º factura", 100),
             ("cliente", "Cliente", 260), ("total", "Total", 140)),
        )
        self.total_entradas = ttk.Label(
            self.pestana_entradas, text="TOTAL ENTRADAS: $0",
            font=("TkDefaultFont", 11, "bold"),
        )
        self.total_entradas.pack(anchor="e", pady=(6, 0))

        self.tabla_salidas = self._crear_tabla(
            self.pestana_salidas,
            (("fecha", "Fecha", 110), ("tipo", "Tipo", 130),
             ("concepto", "Concepto", 300), ("monto", "Monto", 140)),
        )
        self.total_salidas = ttk.Label(
            self.pestana_salidas, text="TOTAL SALIDAS: $0",
            font=("TkDefaultFont", 11, "bold"),
        )
        self.total_salidas.pack(anchor="e", pady=(6, 0))

        ttk.Label(
            self.pestana_corte, text="RESUMEN DEL MES",
            font=("TkDefaultFont", 16, "bold"),
        ).pack(pady=(10, 18))
        self.resumen_labels: dict[str, ttk.Label] = {}
        valores = (
            ("productos", "Ventas de productos"),
            ("servicios", "Servicios cobrados"),
            ("nomina", "Nómina pagada"),
            ("utilidad_bruta", "Utilidad bruta"),
            ("entradas", "Total entradas"),
            ("salidas", "Total salidas"),
            ("balance", "BALANCE DEL MES"),
        )
        panel = ttk.Frame(self.pestana_corte, padding=12)
        panel.pack(anchor="n", fill="x", padx=40)
        for fila, (clave, texto) in enumerate(valores):
            negrita = clave in {"utilidad_bruta", "balance"}
            fuente = ("TkDefaultFont", 11, "bold") if negrita else ("TkDefaultFont", 10)
            ttk.Label(panel, text=texto, font=fuente).grid(
                row=fila, column=0, sticky="w", padx=8, pady=7
            )
            etiqueta = ttk.Label(panel, text="$0", font=fuente)
            etiqueta.grid(row=fila, column=1, sticky="e", padx=8, pady=7)
            self.resumen_labels[clave] = etiqueta
        panel.columnconfigure(1, weight=1)

        pendientes = ttk.Panedwindow(self.pestana_pendientes, orient="vertical")
        pendientes.pack(fill="both", expand=True)
        panel_facturas = ttk.LabelFrame(pendientes, text="Facturas emitidas sin pagar", padding=5)
        panel_gastos = ttk.LabelFrame(pendientes, text="Gastos pendientes", padding=5)
        pendientes.add(panel_facturas, weight=1)
        pendientes.add(panel_gastos, weight=1)
        self.tabla_facturas_pendientes = self._crear_tabla(
            panel_facturas,
            (("cliente", "Cliente", 210), ("numero", "Número", 75),
             ("fecha", "Fecha", 100), ("total", "Total", 120),
             ("mora", "Días de mora", 105)),
        )
        self.tabla_gastos_pendientes = self._crear_tabla(
            panel_gastos,
            (("proveedor", "Proveedor", 180), ("concepto", "Concepto", 260),
             ("fecha", "Fecha", 100), ("monto", "Monto", 120)),
        )

    @staticmethod
    def _crear_tabla(
        contenedor: ttk.Frame, columnas: tuple[tuple[str, str, int], ...]
    ) -> ttk.Treeview:
        marco = ttk.Frame(contenedor)
        marco.pack(fill="both", expand=True)
        tabla = ttk.Treeview(
            marco, columns=tuple(c[0] for c in columnas),
            show="headings", selectmode="browse",
        )
        for nombre, titulo, ancho in columnas:
            tabla.heading(nombre, text=titulo)
            tabla.column(nombre, width=ancho, minwidth=65)
        vertical = ttk.Scrollbar(marco, orient="vertical", command=tabla.yview)
        horizontal = ttk.Scrollbar(marco, orient="horizontal", command=tabla.xview)
        tabla.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        vertical.pack(side="right", fill="y")
        horizontal.pack(side="bottom", fill="x")
        tabla.pack(side="left", fill="both", expand=True)
        return tabla

    def actualizar(self) -> None:
        """Consulta las secciones para un mismo mes/año seleccionado."""
        try:
            mes = int(self.mes.get())
            anio = int(self.anio.get())
            if not 1 <= mes <= 12:
                raise ValueError("Seleccione un mes válido.")
            if not 1900 <= anio <= 2100:
                raise ValueError("El año debe estar entre 1900 y 2100.")
            entradas = database.facturas_pagadas_en_mes(anio, mes)
            gastos = database.gastos_pagados_en_mes(anio, mes)
            desprendibles = database.desprendibles_en_mes(anio, mes)
            resumen = database.resumen_corte_mensual(anio, mes)
            self._llenar_entradas(entradas)
            self._llenar_salidas(gastos, desprendibles)
            self._llenar_resumen(resumen)
            self._llenar_pendientes()
            self.estado(f"Corte mensual actualizado: {mes:02d}/{anio}")
        except ValueError as error:
            messagebox.showerror("Período no válido", str(error))
        except database.ErrorBaseDatos as error:
            messagebox.showerror("Error de historial", str(error))

    def _llenar_entradas(self, facturas: list[dict]) -> None:
        self.tabla_entradas.delete(*self.tabla_entradas.get_children())
        total = 0.0
        for factura in facturas:
            total += float(factura["total"] or 0)
            self.tabla_entradas.insert(
                "", "end", iid=str(factura["id"]),
                values=(
                    fecha_pantalla(factura["fecha_emision"]), factura["numero"],
                    factura["cliente"] or "", formatear_moneda(factura["total"]),
                ),
            )
        self.total_entradas.configure(text=f"TOTAL ENTRADAS: {formatear_moneda(total)}")

    def _llenar_salidas(self, gastos: list[dict], desprendibles: list[dict]) -> None:
        """Combina gastos pagados y desprendibles en una lista de egresos."""
        self.tabla_salidas.delete(*self.tabla_salidas.get_children())
        total = 0.0
        for gasto in gastos:
            total += float(gasto["monto"] or 0)
            concepto = gasto["concepto"]
            if gasto.get("proveedor"):
                concepto += f' — {gasto["proveedor"]}'
            self.tabla_salidas.insert(
                "", "end", iid=f"gasto_{gasto['id']}",
                values=(
                    fecha_pantalla(gasto["fecha_pago"]), "Gasto", concepto,
                    formatear_moneda(gasto["monto"]),
                ),
            )
        for desprendible in desprendibles:
            total += float(desprendible["total"] or 0)
            self.tabla_salidas.insert(
                "", "end", iid=f"desprendible_{desprendible['id']}",
                values=(
                    fecha_pantalla(desprendible["fecha_emision"]), "Desprendible",
                    f'Pago a {desprendible["trabajador"]} (#{desprendible["numero"]})',
                    formatear_moneda(desprendible["total"]),
                ),
            )
        self.total_salidas.configure(text=f"TOTAL SALIDAS: {formatear_moneda(total)}")

    def _llenar_resumen(self, resumen: dict) -> None:
        for clave, etiqueta in self.resumen_labels.items():
            etiqueta.configure(text=formatear_moneda(resumen[clave]))

    def _llenar_pendientes(self) -> None:
        """Muestra obligaciones aún no pagadas, independientes del corte."""
        facturas = database.facturas_pendientes()
        gastos = database.gastos_pendientes()
        self.tabla_facturas_pendientes.delete(*self.tabla_facturas_pendientes.get_children())
        for factura in facturas:
            self.tabla_facturas_pendientes.insert(
                "", "end", iid=str(factura["id"]),
                values=(
                    factura["cliente"] or "", factura["numero"],
                    fecha_pantalla(factura["fecha_emision"]),
                    formatear_moneda(factura["total"]), max(0, factura["dias_mora"] or 0),
                ),
            )
        self.tabla_gastos_pendientes.delete(*self.tabla_gastos_pendientes.get_children())
        for gasto in gastos:
            self.tabla_gastos_pendientes.insert(
                "", "end", iid=str(gasto["id"]),
                values=(
                    gasto["proveedor"] or "", gasto["concepto"],
                    fecha_pantalla(gasto["fecha"]), formatear_moneda(gasto["monto"]),
                ),
            )
