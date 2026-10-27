"""Liquidación de comisiones y consulta de desprendibles."""

import tkinter as tk
from tkinter import messagebox, ttk
from datetime import date
from typing import Callable, Any

import database
from pdf.generador_pdf import ErrorGeneracionPDF, generar_desprendible_pdf
from utils.helpers import fecha_iso, fecha_pantalla, formatear_moneda


class Nomina(ttk.Frame):
    """Consulta comisiones pendientes y registra su liquidación por trabajador."""

    def __init__(self, master: tk.Misc, estado: Callable[[str], None]) -> None:
        super().__init__(master, padding=10)
        self.estado = estado
        self.trabajadores: list[dict[str, Any]] = []
        self.trabajador_por_iid: dict[str, dict[str, Any]] = {}
        self._crear_interfaz()
        self.actualizar()

    def _crear_interfaz(self) -> None:
        ttk.Label(self, text="Nómina y comisiones", font=("TkDefaultFont", 16, "bold")).pack(
            anchor="w", pady=(0, 8)
        )
        cuerpo = ttk.Panedwindow(self, orient="horizontal")
        cuerpo.pack(fill="both", expand=True)
        panel_trabajadores = ttk.LabelFrame(cuerpo, text="Trabajadores activos", padding=6)
        panel_detalle = ttk.Frame(cuerpo, padding=(8, 0, 0, 0))
        cuerpo.add(panel_trabajadores, weight=1)
        cuerpo.add(panel_detalle, weight=3)
        marco_trabajadores = ttk.Frame(panel_trabajadores)
        marco_trabajadores.pack(fill="both", expand=True)
        self.tabla_trabajadores = ttk.Treeview(
            marco_trabajadores, columns=("nombre", "pendiente"),
            show="headings", selectmode="browse", height=18,
        )
        self.tabla_trabajadores.heading("nombre", text="Trabajador")
        self.tabla_trabajadores.heading("pendiente", text="Pendiente")
        self.tabla_trabajadores.column("nombre", width=170)
        self.tabla_trabajadores.column("pendiente", width=115, anchor="e")
        self._agregar_scrollbars(self.tabla_trabajadores)
        self.tabla_trabajadores.bind(
            "<<TreeviewSelect>>",
            lambda evento: self._seleccionar_trabajador()
            if evento.widget is self.tabla_trabajadores else None,
        )

        filtros = ttk.LabelFrame(panel_detalle, text="Período de comisiones", padding=6)
        filtros.pack(fill="x", pady=(0, 6))
        self.incluir_todas = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            filtros, text="Incluir todas las pendientes (ignorar fechas)",
            variable=self.incluir_todas, command=self._cambio_filtro,
        ).grid(row=0, column=0, columnspan=4, sticky="w", padx=4, pady=3)
        ttk.Label(filtros, text="Desde (dd/mm/aaaa)").grid(
            row=1, column=0, sticky="w", padx=4, pady=3
        )
        self.entrada_desde = ttk.Entry(filtros, width=14)
        self.entrada_desde.grid(row=1, column=1, padx=4, pady=3)
        hoy = date.today()
        self.entrada_desde.insert(0, f"01/{hoy.month:02d}/{hoy.year}")
        ttk.Label(filtros, text="Hasta").grid(row=1, column=2, sticky="w", padx=4, pady=3)
        self.entrada_hasta = ttk.Entry(filtros, width=14)
        self.entrada_hasta.grid(row=1, column=3, padx=4, pady=3)
        self.entrada_hasta.insert(0, hoy.strftime("%d/%m/%Y"))
        ttk.Button(filtros, text="Aplicar filtro", command=self._actualizar_comisiones).grid(
            row=1, column=4, padx=4, pady=3
        )

        columnas = ("fecha", "servicio", "porcentaje", "monto")
        marco_comisiones = ttk.Frame(panel_detalle)
        marco_comisiones.pack(fill="both", expand=True)
        self.tabla_comisiones = ttk.Treeview(
            marco_comisiones, columns=columnas, show="headings",
            selectmode="browse", height=8
        )
        for columna, titulo, ancho in (
            ("fecha", "Fecha", 100), ("servicio", "Servicio", 240),
            ("porcentaje", "% aplicado", 100), ("monto", "Monto", 130),
        ):
            self.tabla_comisiones.heading(columna, text=titulo)
            self.tabla_comisiones.column(
                columna, width=ancho, anchor="e" if columna in {"porcentaje", "monto"} else "w"
            )
        self._agregar_scrollbars(self.tabla_comisiones)
        barra = ttk.Frame(panel_detalle)
        barra.pack(fill="x", pady=6)
        ttk.Button(barra, text="Generar desprendible", command=self._generar).pack(
            side="left", padx=3
        )
        ttk.Button(barra, text="Imprimir desprendible PDF", command=self._imprimir_seleccionado).pack(
            side="left", padx=3
        )
        self.total_pendiente = ttk.Label(barra, text="Total seleccionado: $0")
        self.total_pendiente.pack(side="right", padx=6)

        historial = ttk.LabelFrame(panel_detalle, text="Desprendibles generados", padding=6)
        historial.pack(fill="both", expand=True, pady=(6, 0))
        columnas_historial = ("numero", "fecha", "periodo", "total", "estado")
        marco_historial = ttk.Frame(historial)
        marco_historial.pack(fill="both", expand=True)
        self.tabla_desprendibles = ttk.Treeview(
            marco_historial, columns=columnas_historial, show="headings",
            selectmode="browse", height=6,
        )
        for columna, titulo, ancho in (
            ("numero", "N.º", 55), ("fecha", "Emisión", 100),
            ("periodo", "Período", 220), ("total", "Total", 120), ("estado", "Estado", 90),
        ):
            self.tabla_desprendibles.heading(columna, text=titulo)
            self.tabla_desprendibles.column(columna, width=ancho)
        self._agregar_scrollbars(self.tabla_desprendibles)
        ttk.Button(historial, text="Ver PDF", command=self._imprimir_seleccionado).pack(
            anchor="e", pady=(5, 0)
        )
        self.tabla_trabajadores.bind(
            "<Double-1>",
            lambda evento: self._seleccionar_trabajador()
            if evento.widget is self.tabla_trabajadores else None,
        )

    @staticmethod
    def _agregar_scrollbars(tabla: ttk.Treeview) -> None:
        marco = tabla.master
        vertical = ttk.Scrollbar(marco, orient="vertical", command=tabla.yview)
        horizontal = ttk.Scrollbar(marco, orient="horizontal", command=tabla.xview)
        tabla.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        vertical.pack(side="right", fill="y")
        horizontal.pack(side="bottom", fill="x")
        tabla.pack(side="left", fill="both", expand=True)

    def actualizar(self) -> None:
        """Recarga trabajadores, totales pendientes y el historial seleccionado."""
        seleccionado = self._trabajador_actual_id()
        try:
            self.trabajadores = database.trabajadores_listar()
            self.tabla_trabajadores.delete(*self.tabla_trabajadores.get_children())
            self.trabajador_por_iid.clear()
            for trabajador in self.trabajadores:
                pendientes = database.comisiones_listar_pendientes(trabajador["id"])
                total = sum(float(comision["monto"] or 0) for comision in pendientes)
                iid = str(trabajador["id"])
                self.trabajador_por_iid[iid] = trabajador
                self.tabla_trabajadores.insert(
                    "", "end", iid=iid,
                    values=(trabajador["nombre"], formatear_moneda(total)),
                )
            if seleccionado and str(seleccionado) in self.trabajador_por_iid:
                self.tabla_trabajadores.selection_set(str(seleccionado))
            elif self.trabajadores:
                self.tabla_trabajadores.selection_set(str(self.trabajadores[0]["id"]))
            self._seleccionar_trabajador()
        except database.ErrorBaseDatos as error:
            messagebox.showerror("Error de nómina", str(error))

    def _trabajador_actual_id(self) -> int | None:
        seleccion = self.tabla_trabajadores.selection()
        return int(seleccion[0]) if seleccion else None

    def _seleccionar_trabajador(self) -> None:
        trabajador_id = self._trabajador_actual_id()
        self._actualizar_comisiones()
        self._actualizar_desprendibles(trabajador_id)

    def _cambio_filtro(self) -> None:
        estado = "disabled" if self.incluir_todas.get() else "normal"
        self.entrada_desde.configure(state=estado)
        self.entrada_hasta.configure(state=estado)
        self._actualizar_comisiones()

    def _rango_seleccionado(self) -> tuple[str | None, str | None]:
        if self.incluir_todas.get():
            return None, None
        desde_texto = self.entrada_desde.get().strip()
        hasta_texto = self.entrada_hasta.get().strip()
        if not desde_texto or not hasta_texto:
            raise ValueError("Indique las fechas desde y hasta o marque incluir todas.")
        desde = fecha_iso(desde_texto)
        hasta = fecha_iso(hasta_texto)
        if desde > hasta:
            raise ValueError("La fecha desde no puede ser posterior a la fecha hasta.")
        return desde, hasta

    def _actualizar_comisiones(self) -> None:
        """Aplica el rango actual sin alterar qué comisiones siguen pendientes."""
        if not hasattr(self, "tabla_comisiones"):
            return
        self.tabla_comisiones.delete(*self.tabla_comisiones.get_children())
        trabajador_id = self._trabajador_actual_id()
        if trabajador_id is None:
            self.total_pendiente.configure(text="Total seleccionado: $0")
            return
        try:
            if self.incluir_todas.get():
                desde, hasta = None, None
            else:
                desde_texto = self.entrada_desde.get().strip()
                hasta_texto = self.entrada_hasta.get().strip()
                desde = fecha_iso(desde_texto) if desde_texto else None
                hasta = fecha_iso(hasta_texto) if hasta_texto else None
                if desde and hasta and desde > hasta:
                    raise ValueError("La fecha desde no puede ser posterior a la fecha hasta.")
            comisiones = database.comisiones_listar_pendientes(trabajador_id, desde, hasta)
            total = 0.0
            for comision in comisiones:
                total += float(comision["monto"] or 0)
                self.tabla_comisiones.insert(
                    "", "end", iid=str(comision["id"]),
                    values=(
                        fecha_pantalla(comision["fecha_generacion"]),
                        comision["servicio"] or "Servicio",
                        f'{float(comision["porcentaje"] or 0):g}%',
                        formatear_moneda(comision["monto"]),
                    ),
                )
            self.total_pendiente.configure(
                text=f"Total seleccionado: {formatear_moneda(total)}"
            )
        except ValueError as error:
            messagebox.showerror("Período no válido", str(error))
        except database.ErrorBaseDatos as error:
            messagebox.showerror("Error", str(error))

    def _actualizar_desprendibles(self, trabajador_id: int | None) -> None:
        self.tabla_desprendibles.delete(*self.tabla_desprendibles.get_children())
        if trabajador_id is None:
            return
        try:
            for desprendible in database.desprendibles_listar(trabajador_id):
                inicio = fecha_pantalla(desprendible["periodo_inicio"]) or "Todas"
                fin = fecha_pantalla(desprendible["periodo_fin"]) or "Todas"
                self.tabla_desprendibles.insert(
                    "", "end", iid=str(desprendible["id"]),
                    values=(
                        desprendible["numero"], fecha_pantalla(desprendible["fecha_emision"]),
                        f"{inicio} - {fin}", formatear_moneda(desprendible["total"]),
                        desprendible["estado"],
                    ),
                )
        except database.ErrorBaseDatos as error:
            messagebox.showerror("Error", str(error))

    def _generar(self) -> None:
        """Crea el desprendible y delega la liquidación atómica a la base de datos."""
        trabajador_id = self._trabajador_actual_id()
        if trabajador_id is None:
            messagebox.showwarning("Selección requerida", "Seleccione un trabajador.")
            return
        try:
            desde, hasta = self._rango_seleccionado()
            desprendible_id = database.nomina_generar_desprendible(
                trabajador_id, desde, hasta, incluir_todas=self.incluir_todas.get()
            )
            self.actualizar()
            self.tabla_desprendibles.selection_set(str(desprendible_id))
            self.estado("Desprendible generado y comisiones liquidadas")
            messagebox.showinfo("Éxito", "El desprendible se generó correctamente.")
        except ValueError as error:
            messagebox.showerror("Período no válido", str(error))
        except database.ErrorBaseDatos as error:
            messagebox.showerror("Error", str(error))

    def _imprimir_seleccionado(self) -> None:
        """Genera el PDF correspondiente al desprendible resaltado en el historial."""
        seleccion = self.tabla_desprendibles.selection()
        if not seleccion:
            messagebox.showwarning(
                "Selección requerida", "Seleccione un desprendible del historial."
            )
            return
        try:
            desprendible = database.desprendible_obtener(int(seleccion[0]))
            if desprendible is None:
                raise ValueError("El desprendible seleccionado no existe.")
            ruta = generar_desprendible_pdf(desprendible)
            self.estado(f"PDF de desprendible generado: {ruta}")
            messagebox.showinfo("PDF generado", f"Se guardó el archivo en:\n{ruta}")
        except (ValueError, database.ErrorBaseDatos, ErrorGeneracionPDF) as error:
            messagebox.showerror("Error al generar PDF", str(error))
