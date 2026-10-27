"""Administración de facturas, cotizaciones y órdenes del taller."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable

import database
from pdf.generador_pdf import ErrorGeneracionPDF, generar_pdf
from utils.helpers import fecha_hoy_iso, fecha_iso, fecha_pantalla, formatear_moneda
from utils.validaciones import numero_positivo, porcentaje_valido


TIPOS = {
    "Factura": "factura",
    "Cotización": "cotizacion",
    "Orden de Servicio": "orden_servicio",
    "Orden de Trabajo": "orden_trabajo",
}
TIPOS_POR_CLAVE = {valor: llave for llave, valor in TIPOS.items()}
ESTADOS = ("Todos", "emitida", "pagada", "aprobada", "anulada")


class Documentos(ttk.Frame):
    """Interfaz para consultar documentos y ejecutar sus flujos de negocio."""

    def __init__(self, master: tk.Misc, estado: Callable[[str], None]) -> None:
        super().__init__(master, padding=10)
        self.estado = estado
        self._crear_filtros()
        self._crear_tabla()
        self._crear_acciones()
        self.actualizar()

    def _crear_filtros(self) -> None:
        filtros = ttk.LabelFrame(self, text="Filtros", padding=7)
        filtros.pack(fill="x", pady=(0, 8))
        ttk.Label(filtros, text="Tipo").grid(row=0, column=0, padx=4, sticky="w")
        self.filtro_tipo = ttk.Combobox(
            filtros, state="readonly", width=19,
            values=("Todos", *TIPOS.keys()),
        )
        self.filtro_tipo.set("Todos")
        self.filtro_tipo.grid(row=0, column=1, padx=4)
        ttk.Label(filtros, text="Fecha desde (dd/mm/aaaa)").grid(
            row=0, column=2, padx=4, sticky="w"
        )
        self.filtro_desde = ttk.Entry(filtros, width=14)
        self.filtro_desde.grid(row=0, column=3, padx=4)
        ttk.Label(filtros, text="Fecha hasta").grid(row=0, column=4, padx=4, sticky="w")
        self.filtro_hasta = ttk.Entry(filtros, width=14)
        self.filtro_hasta.grid(row=0, column=5, padx=4)
        ttk.Label(filtros, text="Cliente").grid(row=0, column=6, padx=4, sticky="w")
        self.filtro_cliente = ttk.Combobox(filtros, state="readonly", width=20)
        self.filtro_cliente.grid(row=0, column=7, padx=4)
        ttk.Label(filtros, text="Estado").grid(row=0, column=8, padx=4, sticky="w")
        self.filtro_estado = ttk.Combobox(
            filtros, state="readonly", width=12, values=ESTADOS
        )
        self.filtro_estado.set("Todos")
        self.filtro_estado.grid(row=0, column=9, padx=4)
        ttk.Button(filtros, text="Aplicar", command=self.actualizar).grid(
            row=0, column=10, padx=4
        )
        self.clientes: list[dict[str, Any]] = []
        self.clientes_por_nombre: dict[str, int] = {}
        self._actualizar_clientes()

    def _actualizar_clientes(self) -> bool:
        """Sincroniza los selectores con los clientes activos de la base actual."""
        try:
            clientes = database.clientes_listar()
            filtro_actual = self.filtro_cliente.get()
            self.clientes = clientes
            self.clientes_por_nombre = {
                f'{cliente["nombre"]} (#{cliente["id"]})': cliente["id"]
                for cliente in clientes
            }
            self.filtro_cliente.configure(values=("Todos", *self.clientes_por_nombre))
            self.filtro_cliente.set(
                filtro_actual if filtro_actual in self.clientes_por_nombre else "Todos"
            )
            return True
        except database.ErrorBaseDatos as error:
            messagebox.showerror("Error", str(error))
            return False

    def _crear_tabla(self) -> None:
        columnas = ("tipo", "numero", "fecha", "cliente", "total", "estado")
        marco = ttk.Frame(self)
        marco.pack(fill="both", expand=True)
        self.tabla = ttk.Treeview(
            marco, columns=columnas, show="headings", selectmode="browse"
        )
        for columna, titulo, ancho in (
            ("tipo", "Tipo", 150), ("numero", "Número", 75), ("fecha", "Fecha", 100),
            ("cliente", "Cliente", 230), ("total", "Total", 120), ("estado", "Estado", 100),
        ):
            self.tabla.heading(columna, text=titulo)
            self.tabla.column(columna, width=ancho, minwidth=65)
        vertical = ttk.Scrollbar(marco, orient="vertical", command=self.tabla.yview)
        horizontal = ttk.Scrollbar(marco, orient="horizontal", command=self.tabla.xview)
        self.tabla.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        vertical.pack(side="right", fill="y")
        horizontal.pack(side="bottom", fill="x")
        self.tabla.pack(side="left", fill="both", expand=True)
        self.tabla.bind(
            "<<TreeviewSelect>>",
            lambda evento: self._actualizar_botones() if evento.widget is self.tabla else None,
        )
        self.tabla.bind(
            "<Double-1>", lambda evento: self._editar() if evento.widget is self.tabla else None
        )

    def _crear_acciones(self) -> None:
        barra = ttk.Frame(self)
        barra.pack(fill="x", pady=(8, 0))
        botones = (
            ("Nueva Factura", lambda: self._formulario("factura")),
            ("Nueva Cotización", lambda: self._formulario("cotizacion")),
            ("Nueva Orden de Trabajo", lambda: self._formulario("orden_trabajo")),
            ("Nueva Orden de Servicio", lambda: self._formulario("orden_servicio")),
            ("Ver / Editar", self._editar),
            ("Imprimir PDF", self._imprimir_pdf),
        )
        for texto, comando in botones:
            ttk.Button(barra, text=texto, command=comando).pack(side="left", padx=2)
        self.boton_pagada = ttk.Button(
            barra, text="Marcar como pagada", command=self._marcar_pagada
        )
        self.boton_pagada.pack(side="left", padx=2)
        self.boton_aprobar_cotizacion = ttk.Button(
            barra, text="Aprobar cotización", command=self._aprobar_cotizacion
        )
        self.boton_aprobar_cotizacion.pack(side="left", padx=2)
        ttk.Button(barra, text="Eliminar", command=self._eliminar).pack(
            side="right", padx=2
        )
        self._actualizar_botones()

    def abrir_nuevo(self, tipo: str) -> None:
        self._formulario(tipo)

    def _filtros_actuales(self) -> dict[str, Any]:
        filtros: dict[str, Any] = {}
        etiqueta_tipo = self.filtro_tipo.get()
        if etiqueta_tipo != "Todos":
            filtros["tipo"] = TIPOS[etiqueta_tipo]
        etiqueta_cliente = self.filtro_cliente.get()
        if etiqueta_cliente in self.clientes_por_nombre:
            filtros["cliente_id"] = self.clientes_por_nombre[etiqueta_cliente]
        if self.filtro_estado.get() != "Todos":
            filtros["estado"] = self.filtro_estado.get()
        for campo, entrada in (
            ("fecha_desde", self.filtro_desde), ("fecha_hasta", self.filtro_hasta),
        ):
            texto = entrada.get().strip()
            if texto:
                try:
                    filtros[campo] = fecha_iso(texto)
                except ValueError as error:
                    raise ValueError(
                        f"Fecha no válida en «{campo.replace('_', ' ')}». Use dd/mm/aaaa."
                    ) from error
        if filtros.get("fecha_desde") and filtros.get("fecha_hasta"):
            if filtros["fecha_desde"] > filtros["fecha_hasta"]:
                raise ValueError("La fecha desde no puede ser posterior a la fecha hasta.")
        return filtros

    def actualizar(self) -> None:
        try:
            if not self._actualizar_clientes():
                return
            filtros = self._filtros_actuales()
            filas = database.documentos_listar(filtros)
            self.tabla.delete(*self.tabla.get_children())
            for documento in filas:
                self.tabla.insert(
                    "", "end", iid=str(documento["id"]),
                    values=(
                        TIPOS_POR_CLAVE.get(documento["tipo"], documento["tipo"]),
                        documento["numero"], fecha_pantalla(documento["fecha_emision"]),
                        documento["cliente"] or "", formatear_moneda(documento["total"]),
                        documento["estado"],
                    ),
                )
            self._actualizar_botones()
        except ValueError as error:
            messagebox.showerror("Filtro no válido", str(error))
        except database.ErrorBaseDatos as error:
            messagebox.showerror("Error", str(error))

    def _seleccionado(self) -> dict[str, Any] | None:
        seleccion = self.tabla.selection()
        if not seleccion:
            messagebox.showwarning("Selección requerida", "Seleccione un documento primero.")
            return None
        try:
            documento = database.documentos_obtener(int(seleccion[0]))
        except database.ErrorBaseDatos as error:
            messagebox.showerror("Error", str(error))
            return None
        if documento is None:
            messagebox.showerror("Error", "El documento seleccionado ya no existe.")
        return documento

    def _actualizar_botones(self) -> None:
        """Habilita acciones según tipo, estado y composición del documento."""
        seleccion = self.tabla.selection()
        documento = None
        if seleccion:
            try:
                documento = database.documentos_obtener(int(seleccion[0]))
            except database.ErrorBaseDatos as error:
                self.estado(f"Error al leer el documento: {error}")
                documento = None
        self.boton_pagada.configure(
            state="normal" if documento and documento["tipo"] == "factura"
            and documento["estado"] == "emitida" else "disabled"
        )
        cotizacion = documento and documento["tipo"] == "cotizacion" and documento["estado"] != "aprobada"
        self.boton_aprobar_cotizacion.configure(
            state="normal" if cotizacion else "disabled"
        )

    def _editar(self) -> None:
        documento = self._seleccionado()
        if documento is None:
            return
        if not messagebox.askyesno(
            "Confirmar edición",
            "Los cambios recalcularán inventario y comisiones asociadas. ¿Desea continuar?",
        ):
            return
        self._formulario(documento["tipo"], documento)

    def _formulario(
        self,
        tipo: str,
        documento: dict[str, Any] | None = None,
        documento_origen_id: int | None = None,
    ) -> None:
        """Construye el formulario y deja el guardado transaccional en database."""
        if tipo not in TIPOS.values():
            messagebox.showerror("Error", "Tipo de documento no reconocido.")
            return
        if not self._actualizar_clientes():
            return
        ventana = tk.Toplevel(self)
        editando = documento is not None and documento_origen_id is None
        ventana.title(
            f"{'Editar' if editando else 'Nueva'} {TIPOS_POR_CLAVE[tipo].lower()}"
        )
        ventana.transient(self.winfo_toplevel())
        ventana.grab_set()
        ventana.geometry("1000x710")
        ventana.minsize(850, 600)
        principal = ttk.Frame(ventana, padding=10)
        principal.pack(fill="both", expand=True)

        campos: dict[str, ttk.Entry] = {}
        cliente_nombre = ""
        if documento and documento.get("cliente_id"):
            cliente = next(
                (c for c in self.clientes if c["id"] == documento["cliente_id"]), None
            )
            cliente_nombre = (
                f'{cliente["nombre"]} (#{cliente["id"]})' if cliente
                else f'{documento.get("cliente", "Cliente")} (#{documento["cliente_id"]})'
            )
        cliente_valores = list(self.clientes_por_nombre)
        ttk.Label(principal, text="Cliente").grid(row=0, column=0, sticky="w", padx=4, pady=3)
        cliente_combo = ttk.Combobox(
            principal, state="readonly", values=cliente_valores, width=38
        )
        cliente_combo.grid(row=0, column=1, sticky="ew", padx=4, pady=3)
        if cliente_nombre:
            cliente_combo.set(cliente_nombre)
        ttk.Label(principal, text="Fecha de emisión (dd/mm/aaaa)").grid(
            row=0, column=2, sticky="w", padx=4, pady=3
        )
        fecha = ttk.Entry(principal, width=18)
        fecha.insert(
            0, fecha_pantalla(documento["fecha_emision"])
            if documento else fecha_pantalla(fecha_hoy_iso())
        )
        fecha.grid(row=0, column=3, sticky="w", padx=4, pady=3)

        campos_documento = [
            ("Requerimiento / falla reportada", "falla_reportada"),
        ]
        if tipo in {"orden_servicio", "orden_trabajo"}:
            campos_documento.extend([
                ("Fecha de inicio (dd/mm/aaaa)", "fecha_inicio"),
                ("Fecha de entrega (dd/mm/aaaa)", "fecha_entrega"),
                ("Equipo", "equipo"),
                ("Placa", "placa"),
                ("Serial / OT", "serial_ot"),
                ("Tiempo estimado", "tiempo_estimado"),
            ])
        if tipo == "orden_servicio":
            campos_documento.extend([
                ("Causa de falla", "causa_falla"),
                ("Trabajos ejecutados", "trabajos_ejecutados"),
                ("Recomendaciones", "recomendaciones"),
            ])
        campos_documento.append(("Notas", "notas"))

        fila_campo = 1
        for etiqueta, clave in campos_documento:
            ttk.Label(principal, text=etiqueta).grid(
                row=fila_campo, column=0, sticky="w", padx=4, pady=3
            )
            entrada = ttk.Entry(principal, width=42)
            valor = documento.get(clave, "") if documento else ""
            if clave in {"fecha_inicio", "fecha_entrega"}:
                valor = fecha_pantalla(valor)
            entrada.insert(0, valor or "")
            entrada.grid(row=fila_campo, column=1, columnspan=3, sticky="ew", padx=4, pady=3)
            campos[clave] = entrada
            fila_campo += 1

        marco_detalle = ttk.LabelFrame(principal, text="Detalle del documento", padding=6)
        marco_detalle.grid(
            row=fila_campo, column=0, columnspan=4, sticky="nsew", padx=3, pady=6
        )
        columnas = ("tipo", "descripcion", "cantidad", "precio", "subtotal", "trabajadores")
        marco_tabla = ttk.Frame(marco_detalle)
        marco_tabla.pack(fill="both", expand=True)
        tabla = ttk.Treeview(
            marco_tabla, columns=columnas, show="headings", height=8,
            selectmode="browse"
        )
        for columna, titulo, ancho in (
            ("tipo", "Tipo", 95), ("descripcion", "Artículo / servicio", 240),
            ("cantidad", "Cantidad", 80), ("precio", "Precio unitario", 120),
            ("subtotal", "Subtotal", 120), ("trabajadores", "Trabajadores y %", 210),
        ):
            tabla.heading(columna, text=titulo)
            tabla.column(columna, width=ancho, minwidth=60)
        scroll_v = ttk.Scrollbar(marco_tabla, orient="vertical", command=tabla.yview)
        scroll_h = ttk.Scrollbar(marco_tabla, orient="horizontal", command=tabla.xview)
        tabla.configure(yscrollcommand=scroll_v.set, xscrollcommand=scroll_h.set)
        scroll_v.pack(side="right", fill="y")
        scroll_h.pack(side="bottom", fill="x")
        tabla.pack(side="left", fill="both", expand=True)
        lineas = [
            {
                "item_tipo": linea["item_tipo"], "item_id": linea["item_id"],
                "cantidad": linea["cantidad"], "precio_unitario": linea["precio_unitario"],
                "subtotal": linea["subtotal"], "descripcion": linea["descripcion"],
                "trabajadores": list(linea.get("trabajadores", [])),
            }
            for linea in (documento.get("detalle", []) if documento else [])
        ]
        etiqueta_total = ttk.Label(marco_detalle, text="Subtotal: $0")
        etiqueta_total.pack(anchor="e", padx=6, pady=4)

        def refrescar_lineas() -> None:
            tabla.delete(*tabla.get_children())
            total = 0.0
            for indice, linea in enumerate(lineas):
                total += linea["subtotal"]
                asignaciones = ", ".join(
                    f'{asignacion.get("trabajador", asignacion.get("nombre", ""))}'
                    f' {asignacion["porcentaje"]:g}%'
                    for asignacion in linea.get("trabajadores", [])
                )
                tabla.insert(
                    "", "end", iid=str(indice),
                    values=(
                        "Producto" if linea["item_tipo"] == "producto" else "Servicio",
                        linea.get("descripcion", ""), f'{linea["cantidad"]:g}',
                        formatear_moneda(linea["precio_unitario"]),
                        formatear_moneda(linea["subtotal"]), asignaciones,
                    ),
                )
            etiqueta_total.configure(
                text=f"Subtotal: {formatear_moneda(total)}    Total: {formatear_moneda(total)}"
            )

        def agregar_linea() -> None:
            self._formulario_linea(ventana, tipo, lineas, refrescar_lineas)

        def quitar_linea() -> None:
            seleccion = tabla.selection()
            if not seleccion:
                messagebox.showwarning("Selección requerida", "Seleccione una línea.")
                return
            lineas.pop(int(seleccion[0]))
            refrescar_lineas()

        acciones_detalle = ttk.Frame(marco_detalle)
        acciones_detalle.pack(fill="x")
        ttk.Button(acciones_detalle, text="Agregar línea", command=agregar_linea).pack(
            side="left", padx=3
        )
        ttk.Button(acciones_detalle, text="Quitar línea", command=quitar_linea).pack(
            side="left", padx=3
        )
        refrescar_lineas()
        principal.columnconfigure(1, weight=1)
        principal.columnconfigure(3, weight=1)
        principal.rowconfigure(fila_campo, weight=1)

        def guardar(
            generar_os_despues: bool = False,
            generar_factura_despues: bool = False,
        ) -> None:
            try:
                cliente_id = self.clientes_por_nombre.get(cliente_combo.get())
                if cliente_id is None:
                    raise ValueError("Seleccione un cliente.")
                fecha_emision = fecha_iso(fecha.get())
                datos: dict[str, Any] = {
                    "tipo": tipo,
                    "fecha_emision": fecha_emision,
                    "cliente_id": cliente_id,
                    "estado": documento.get("estado", "emitida") if editando else "emitida",
                }
                if documento_origen_id is not None:
                    datos["documento_origen_id"] = documento_origen_id
                for clave, entrada in campos.items():
                    valor = entrada.get().strip()
                    if clave in {"fecha_inicio", "fecha_entrega"}:
                        valor = fecha_iso(valor) if valor else None
                    datos[clave] = valor
                lineas_validas = []
                for linea in lineas:
                    asignaciones = []
                    for asignacion in linea.get("trabajadores", []):
                        asignaciones.append({
                            "trabajador_id": asignacion["trabajador_id"],
                            "porcentaje": asignacion["porcentaje"],
                        })
                    lineas_validas.append({
                        "item_tipo": linea["item_tipo"],
                        "item_id": linea["item_id"],
                        "cantidad": linea["cantidad"],
                        "precio_unitario": linea["precio_unitario"],
                        "trabajadores": asignaciones,
                    })
                if tipo == "orden_trabajo" and not any(
                    linea["item_tipo"] == "servicio" for linea in lineas_validas
                ):
                    raise ValueError("La orden de trabajo debe incluir al menos un servicio.")
                documento_guardado_id = database.documentos_guardar_flujo(
                    datos, lineas_validas,
                    documento["id"] if editando and documento else None,
                )
                factura_id = (
                    database.documentos_factura_generar_desde_os(documento_guardado_id)
                    if generar_factura_despues else None
                )
                ventana.destroy()
                self.actualizar()
                if not editando:
                    iid = str(documento_guardado_id)
                    if self.tabla.exists(iid):
                        self.tabla.selection_set(iid)
                        self.tabla.focus(iid)
                if generar_factura_despues and factura_id is not None:
                    self.estado("Orden de servicio guardada y factura generada")
                    factura = database.documentos_obtener(factura_id)
                    numero = factura["numero"] if factura else factura_id
                    messagebox.showinfo(
                        "Éxito", f"Se guardó la orden de servicio y se creó la factura #{numero}."
                    )
                else:
                    self.estado(f"{TIPOS_POR_CLAVE[tipo]} guardado correctamente")
                    messagebox.showinfo(
                        "Éxito",
                        "Documento guardado correctamente."
                        + (
                            "\nLa orden de servicio quedó asociada a la OT. "
                            "Se abrirá para que genere la factura."
                            if tipo == "orden_servicio" and documento_origen_id is not None
                            else "\nSe generó automáticamente la factura."
                            if tipo == "orden_servicio" and documento_origen_id is None
                            else ""
                        ),
                        parent=self.winfo_toplevel(),
                    )
                if generar_os_despues:
                    self._generar_os_desde_id(documento_guardado_id)
                elif (
                    not editando
                    and tipo == "orden_servicio"
                    and documento_origen_id is not None
                ):
                    orden_servicio = database.documentos_obtener(documento_guardado_id)
                    if orden_servicio is not None:
                        self._formulario("orden_servicio", orden_servicio)
            except ValueError as error:
                messagebox.showerror("Dato no válido", str(error), parent=ventana)
            except database.ErrorBaseDatos as error:
                messagebox.showerror("Error", str(error), parent=ventana)

        botones = ttk.Frame(principal)
        botones.grid(row=fila_campo + 1, column=0, columnspan=4, pady=(4, 0))
        ttk.Button(botones, text="Guardar", command=guardar).pack(side="left", padx=5)
        puede_generar_os = tipo == "orden_trabajo" and not editando
        if editando and tipo == "orden_trabajo" and documento:
            try:
                puede_generar_os = not database.documentos_derivado_existe(
                    "orden_servicio", documento["id"]
                )
            except database.ErrorBaseDatos as error:
                ventana.destroy()
                messagebox.showerror("Error", str(error))
                return
        if puede_generar_os:
            ttk.Button(
                botones,
                text="Guardar y generar OS",
                command=lambda: guardar(generar_os_despues=True),
            ).pack(side="left", padx=5)
        if (
            editando
            and tipo == "orden_servicio"
            and documento
            and documento.get("documento_origen_id") is not None
        ):
            try:
                factura_generada = database.documentos_derivado_existe(
                    "factura", documento["id"]
                )
            except database.ErrorBaseDatos as error:
                ventana.destroy()
                messagebox.showerror("Error", str(error))
                return
            if not factura_generada:
                def generar_factura() -> None:
                    guardar(generar_factura_despues=True)

                ttk.Button(
                    botones, text="Generar factura", command=generar_factura
                ).pack(side="left", padx=5)
        ttk.Button(botones, text="Cancelar", command=ventana.destroy).pack(side="left", padx=5)
        ventana.protocol("WM_DELETE_WINDOW", ventana.destroy)
        ventana.wait_window()

    def _formulario_linea(
        self, padre: tk.Toplevel, tipo_documento: str, lineas: list[dict[str, Any]],
        al_guardar: Callable[[], None],
    ) -> None:
        """Añade una línea validada, con hasta dos asignaciones para una OS."""
        ventana = tk.Toplevel(padre)
        ventana.title("Agregar línea")
        ventana.transient(padre)
        ventana.grab_set()
        marco = ttk.Frame(ventana, padding=12)
        marco.pack(fill="both", expand=True)
        ttk.Label(marco, text="Tipo de artículo").grid(row=0, column=0, sticky="w", pady=4)
        tipo_item = ttk.Combobox(
            marco, state="readonly", values=("Producto", "Servicio"), width=30
        )
        tipo_item.set("Producto")
        tipo_item.grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Label(marco, text="Artículo").grid(row=1, column=0, sticky="w", pady=4)
        item_combo = ttk.Combobox(marco, state="readonly", width=42)
        item_combo.grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Label(marco, text="Cantidad").grid(row=2, column=0, sticky="w", pady=4)
        cantidad = ttk.Entry(marco)
        cantidad.insert(0, "1")
        cantidad.grid(row=2, column=1, sticky="ew", pady=4)
        ttk.Label(marco, text="Precio unitario").grid(row=3, column=0, sticky="w", pady=4)
        precio = ttk.Entry(marco)
        precio.insert(0, "0")
        precio.grid(row=3, column=1, sticky="ew", pady=4)
        try:
            trabajadores = database.trabajadores_listar()
        except database.ErrorBaseDatos as error:
            ventana.destroy()
            messagebox.showerror("Error", str(error), parent=padre)
            return
        trabajadores_map = {f'{t["nombre"]} (#{t["id"]})': t["id"] for t in trabajadores}
        combos_trabajador: list[ttk.Combobox] = []
        entradas_porcentaje: list[ttk.Entry] = []
        marco_asignaciones = ttk.LabelFrame(marco, text="Asignación de servicio", padding=6)
        marco_asignaciones.grid(row=4, column=0, columnspan=2, sticky="ew", pady=6)
        numero_asignaciones = 2 if tipo_documento == "orden_servicio" else 1
        for indice in range(numero_asignaciones):
            ttk.Label(marco_asignaciones, text=f"Trabajador {indice + 1}").grid(
                row=indice, column=0, sticky="w", padx=3, pady=3
            )
            combo = ttk.Combobox(
                marco_asignaciones, state="readonly", values=list(trabajadores_map), width=29
            )
            combo.grid(row=indice, column=1, padx=3, pady=3)
            combos_trabajador.append(combo)
            ttk.Label(marco_asignaciones, text="%").grid(
                row=indice, column=2, padx=3, pady=3
            )
            porcentaje = ttk.Entry(marco_asignaciones, width=9)
            porcentaje.insert(0, "0")
            porcentaje.grid(row=indice, column=3, padx=3, pady=3)
            entradas_porcentaje.append(porcentaje)
        marco_asignaciones.grid_remove()
        items: list[dict[str, Any]] = []
        por_etiqueta: dict[str, dict[str, Any]] = {}

        def cargar_items(_evento: object = None) -> None:
            del _evento
            nonlocal items, por_etiqueta
            es_producto = tipo_item.get() == "Producto"
            try:
                items = database.productos_listar() if es_producto else database.servicios_listar()
            except database.ErrorBaseDatos as error:
                messagebox.showerror("Error", str(error), parent=ventana)
                items = []
            por_etiqueta = {}
            opciones = []
            for item in items:
                valor_precio = item["precio_venta"] if es_producto else item["precio_cliente"]
                etiqueta = f'{item["nombre"]} — {formatear_moneda(valor_precio)}'
                opciones.append(etiqueta)
                por_etiqueta[etiqueta] = item
            item_combo.configure(values=opciones)
            item_combo.set(opciones[0] if opciones else "")
            al_seleccionar_item()
            if not es_producto and tipo_documento in {"orden_servicio", "orden_trabajo"}:
                marco_asignaciones.grid()
            else:
                marco_asignaciones.grid_remove()

        def al_seleccionar_item(_evento: object = None) -> None:
            del _evento
            item = por_etiqueta.get(item_combo.get())
            if not item:
                return
            valor_precio = item["precio_venta"] if tipo_item.get() == "Producto" else item["precio_cliente"]
            precio.delete(0, "end")
            precio.insert(0, str(valor_precio))
            if tipo_item.get() == "Servicio":
                for entrada in entradas_porcentaje:
                    entrada.delete(0, "end")
                    entrada.insert(0, str(item["porcentaje_default"]))

        tipo_item.bind(
            "<<ComboboxSelected>>",
            lambda evento: cargar_items() if evento.widget is tipo_item else None,
        )
        item_combo.bind(
            "<<ComboboxSelected>>",
            lambda evento: al_seleccionar_item() if evento.widget is item_combo else None,
        )
        cargar_items()

        def guardar_linea() -> None:
            try:
                item = por_etiqueta.get(item_combo.get())
                if not item:
                    raise ValueError("Seleccione un artículo o servicio.")
                cantidad_valor = numero_positivo(cantidad.get(), "Cantidad", permitir_cero=False)
                if tipo_item.get() == "Producto":
                    if not cantidad_valor.is_integer():
                        raise ValueError("La cantidad de producto debe ser un número entero.")
                precio_valor = numero_positivo(precio.get(), "Precio unitario")
                asignaciones = []
                if tipo_item.get() == "Servicio" and tipo_documento in {
                    "orden_servicio", "orden_trabajo"
                }:
                    for combo, porcentaje in zip(combos_trabajador, entradas_porcentaje):
                        seleccionado = trabajadores_map.get(combo.get())
                        if seleccionado is None:
                            continue
                        asignaciones.append({
                            "trabajador_id": seleccionado,
                            "trabajador": combo.get().rsplit(" (#", 1)[0],
                            "porcentaje": porcentaje_valido(porcentaje.get()),
                        })
                    if not asignaciones:
                        raise ValueError("Asigne al menos un trabajador al servicio.")
                    if len({x["trabajador_id"] for x in asignaciones}) != len(asignaciones):
                        raise ValueError("Seleccione trabajadores distintos en cada asignación.")
                lineas.append({
                    "item_tipo": "producto" if tipo_item.get() == "Producto" else "servicio",
                    "item_id": item["id"],
                    "descripcion": item["nombre"],
                    "cantidad": cantidad_valor,
                    "precio_unitario": precio_valor,
                    "subtotal": cantidad_valor * precio_valor,
                    "trabajadores": asignaciones,
                })
                ventana.destroy()
                al_guardar()
            except ValueError as error:
                messagebox.showerror("Dato no válido", str(error), parent=ventana)

        ttk.Button(marco, text="Agregar", command=guardar_linea).grid(
            row=5, column=0, columnspan=2, pady=8
        )
        marco.columnconfigure(1, weight=1)
        ventana.protocol("WM_DELETE_WINDOW", ventana.destroy)
        ventana.wait_window()

    def _aprobar_cotizacion(self) -> None:
        documento = self._seleccionado()
        if documento is None:
            return
        tiene_servicios = any(
            linea["item_tipo"] == "servicio" for linea in documento["detalle"]
        )
        if not messagebox.askyesno(
            "Aprobar cotización",
            "Se creará una orden de trabajo. ¿Continuar?"
            if tiene_servicios else
            "Esta cotización solo contiene productos; se creará una factura y se "
            "descontará del inventario. ¿Continuar?",
        ):
            return
        if not tiene_servicios:
            self._guardar_aprobacion_cotizacion(documento, None)
            return
        try:
            trabajadores = database.trabajadores_listar()
        except database.ErrorBaseDatos as error:
            messagebox.showerror("Error", str(error))
            return
        if not trabajadores:
            messagebox.showerror(
                "Trabajadores requeridos", "Registre un trabajador antes de aprobar esta cotización."
            )
            return
        ventana = tk.Toplevel(self)
        ventana.title("Asignar trabajador")
        ventana.transient(self.winfo_toplevel())
        ventana.grab_set()
        marco = ttk.Frame(ventana, padding=12)
        marco.pack(fill="both", expand=True)
        ttk.Label(marco, text="Trabajador asignado a la orden").pack(anchor="w", pady=4)
        opciones = {f'{trabajador["nombre"]} (#{trabajador["id"]})': trabajador["id"]
                    for trabajador in trabajadores}
        combo = ttk.Combobox(marco, state="readonly", values=list(opciones), width=35)
        combo.pack(fill="x", pady=4)
        combo.current(0)

        def aprobar() -> None:
            trabajador_id = opciones.get(combo.get())
            if trabajador_id is None:
                messagebox.showwarning(
                    "Selección requerida", "Seleccione un trabajador.", parent=ventana
                )
                return
            ventana.destroy()
            self._guardar_aprobacion_cotizacion(documento, trabajador_id)

        ttk.Button(marco, text="Continuar", command=aprobar).pack(pady=8)
        ventana.wait_window()

    def _guardar_aprobacion_cotizacion(
        self, cotizacion: dict[str, Any], trabajador_id: int | None
    ) -> None:
        try:
            documento_id = database.documentos_aprobar_cotizacion(
                cotizacion["id"], trabajador_id
            )
            documento = database.documentos_obtener(documento_id)
            self.actualizar()
            if documento and documento["tipo"] == "orden_trabajo":
                self.estado("Cotización aprobada; orden de trabajo creada")
                mensaje = f"Se creó la orden de trabajo #{documento['numero']}."
            else:
                self.estado("Cotización aprobada y factura creada")
                numero = documento["numero"] if documento else documento_id
                mensaje = f"Se creó la factura #{numero}."
            messagebox.showinfo("Éxito", mensaje)
        except (ValueError, database.ErrorBaseDatos) as error:
            messagebox.showerror("No se pudo aprobar", str(error))

    def _generar_os_desde_id(self, trabajo_id: int) -> None:
        try:
            trabajo = database.documentos_obtener(trabajo_id)
            if trabajo is None or trabajo["tipo"] != "orden_trabajo":
                raise ValueError("La orden de trabajo seleccionada ya no existe.")
            if database.documentos_derivado_existe("orden_servicio", trabajo_id):
                messagebox.showwarning(
                    "Orden de servicio existente",
                    "Esta orden de trabajo ya tiene una orden de servicio.",
                )
                return
            plantilla = {
                **trabajo,
                "fecha_emision": fecha_hoy_iso(),
                "estado": "emitida",
            }
            self._formulario(
                "orden_servicio", plantilla, documento_origen_id=trabajo_id
            )
        except (ValueError, database.ErrorBaseDatos) as error:
            messagebox.showerror("Error", str(error))

    def _marcar_pagada(self) -> None:
        documento = self._seleccionado()
        if documento is None:
            return
        if not messagebox.askyesno("Confirmar", "¿Marcar esta factura como pagada?"):
            return
        try:
            database.documentos_marcar_pagada(documento["id"])
            self.actualizar()
            self.estado("Factura marcada como pagada")
            messagebox.showinfo("Éxito", "La factura se marcó como pagada.")
        except (ValueError, database.ErrorBaseDatos) as error:
            messagebox.showerror("Error", str(error))

    def _eliminar(self) -> None:
        documento = self._seleccionado()
        if documento is None:
            return
        mensaje = (
            "¿Eliminar este documento y los documentos derivados? "
            "El inventario asociado se repondrá."
        )
        if not messagebox.askyesno("Confirmar eliminación", mensaje):
            return
        try:
            database.documentos_eliminar(documento["id"])
            self.actualizar()
            self.estado("Documento eliminado")
            messagebox.showinfo("Éxito", "El documento se eliminó correctamente.")
        except (ValueError, database.ErrorBaseDatos) as error:
            messagebox.showerror("No se pudo eliminar", str(error))

    def _imprimir_pdf(self) -> None:
        documento = self._seleccionado()
        if documento is None:
            return
        try:
            ruta = generar_pdf(documento)
            self.estado(f"PDF generado: {ruta}")
            messagebox.showinfo("PDF generado", f"El archivo se guardó en:\n{ruta}")
        except ErrorGeneracionPDF as error:
            messagebox.showerror("Error al generar PDF", str(error))
