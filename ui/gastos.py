"""Registro y consulta de gastos operativos."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable

import database
from utils.helpers import fecha_hoy_iso, fecha_iso, fecha_pantalla, formatear_moneda
from utils.validaciones import numero_positivo, texto_obligatorio


class Gastos(ttk.Frame):
    """Interfaz de gastos y mantenimiento de sus categorías."""

    def __init__(self, master: tk.Misc, estado: Callable[[str], None]) -> None:
        super().__init__(master, padding=10)
        self.estado = estado
        self.categorias: list[dict[str, Any]] = []
        self.proveedores: list[dict[str, Any]] = []
        self._crear_interfaz()
        self.actualizar()

    def _crear_interfaz(self) -> None:
        self.pestanas = ttk.Notebook(self)
        self.pestanas.pack(fill="both", expand=True)
        self.pestana_gastos = ttk.Frame(self.pestanas, padding=8)
        self.pestana_categorias = ttk.Frame(self.pestanas, padding=8)
        self.pestanas.add(self.pestana_gastos, text="Gastos")
        self.pestanas.add(self.pestana_categorias, text="Categorías")
        self._crear_gastos()
        self._crear_categorias()

    def _crear_gastos(self) -> None:
        filtros = ttk.LabelFrame(self.pestana_gastos, text="Filtros", padding=6)
        filtros.pack(fill="x", pady=(0, 7))
        ttk.Label(filtros, text="Desde (dd/mm/aaaa)").grid(row=0, column=0, padx=3)
        self.filtro_desde = ttk.Entry(filtros, width=13)
        self.filtro_desde.grid(row=0, column=1, padx=3)
        ttk.Label(filtros, text="Hasta").grid(row=0, column=2, padx=3)
        self.filtro_hasta = ttk.Entry(filtros, width=13)
        self.filtro_hasta.grid(row=0, column=3, padx=3)
        ttk.Label(filtros, text="Categoría").grid(row=0, column=4, padx=3)
        self.filtro_categoria = ttk.Combobox(filtros, state="readonly", width=18)
        self.filtro_categoria.grid(row=0, column=5, padx=3)
        ttk.Label(filtros, text="Estado").grid(row=0, column=6, padx=3)
        self.filtro_estado = ttk.Combobox(
            filtros, state="readonly", values=("Todos", "pagado", "pendiente"), width=12
        )
        self.filtro_estado.set("Todos")
        self.filtro_estado.grid(row=0, column=7, padx=3)
        ttk.Button(filtros, text="Aplicar", command=self.actualizar).grid(
            row=0, column=8, padx=3
        )

        barra = ttk.Frame(self.pestana_gastos)
        barra.pack(fill="x", pady=(0, 6))
        ttk.Button(barra, text="Nuevo", command=self._nuevo).pack(side="left", padx=3)
        ttk.Button(barra, text="Editar", command=self._editar).pack(side="left", padx=3)
        ttk.Button(barra, text="Eliminar", command=self._eliminar).pack(side="left", padx=3)
        self.boton_pagado = ttk.Button(
            barra, text="Marcar como pagado", command=self._marcar_pagado
        )
        self.boton_pagado.pack(side="left", padx=3)
        columnas = ("fecha", "categoria", "concepto", "proveedor", "monto", "estado")
        marco = ttk.Frame(self.pestana_gastos)
        marco.pack(fill="both", expand=True)
        self.tabla = ttk.Treeview(
            marco, columns=columnas, show="headings", selectmode="browse"
        )
        for columna, titulo, ancho in (
            ("fecha", "Fecha", 100), ("categoria", "Categoría", 150),
            ("concepto", "Concepto", 270), ("proveedor", "Proveedor", 200),
            ("monto", "Monto", 120), ("estado", "Estado", 100),
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
            lambda evento: self._actualizar_boton_pagado()
            if evento.widget is self.tabla else None,
        )
        self.tabla.bind(
            "<Double-1>", lambda evento: self._editar() if evento.widget is self.tabla else None
        )

    def _crear_categorias(self) -> None:
        barra = ttk.Frame(self.pestana_categorias)
        barra.pack(fill="x", pady=(0, 6))
        ttk.Button(barra, text="Nueva categoría", command=self._nueva_categoria).pack(
            side="left", padx=3
        )
        ttk.Button(barra, text="Editar", command=self._editar_categoria).pack(
            side="left", padx=3
        )
        ttk.Button(barra, text="Eliminar", command=self._eliminar_categoria).pack(
            side="left", padx=3
        )
        marco = ttk.Frame(self.pestana_categorias)
        marco.pack(fill="both", expand=True)
        self.tabla_categorias = ttk.Treeview(
            marco, columns=("nombre",), show="headings", selectmode="browse",
        )
        self.tabla_categorias.heading("nombre", text="Nombre")
        self.tabla_categorias.column("nombre", width=320)
        vertical = ttk.Scrollbar(marco, orient="vertical", command=self.tabla_categorias.yview)
        horizontal = ttk.Scrollbar(marco, orient="horizontal", command=self.tabla_categorias.xview)
        self.tabla_categorias.configure(
            yscrollcommand=vertical.set, xscrollcommand=horizontal.set
        )
        vertical.pack(side="right", fill="y")
        horizontal.pack(side="bottom", fill="x")
        self.tabla_categorias.pack(side="left", fill="both", expand=True)

    def _cargar_catalogos(self) -> None:
        self.categorias = database.categorias_gasto_listar()
        self.proveedores = database.proveedores_listar()
        etiquetas = {c["nombre"]: c["id"] for c in self.categorias}
        self.categoria_por_nombre = etiquetas
        filtro_actual = self.filtro_categoria.get() if self.filtro_categoria.get() else "Todos"
        self.filtro_categoria.configure(values=("Todos", *etiquetas))
        self.filtro_categoria.set(
            filtro_actual if filtro_actual == "Todos" or filtro_actual in etiquetas else "Todos"
        )
        self.tabla_categorias.delete(*self.tabla_categorias.get_children())
        for categoria in self.categorias:
            self.tabla_categorias.insert(
                "", "end", iid=str(categoria["id"]), values=(categoria["nombre"],)
            )

    def actualizar(self) -> None:
        """Carga catálogos y vuelve a consultar los gastos con los filtros actuales."""
        try:
            self._cargar_catalogos()
            filtros: dict[str, Any] = {}
            desde_texto = self.filtro_desde.get().strip()
            hasta_texto = self.filtro_hasta.get().strip()
            if desde_texto:
                filtros["fecha_desde"] = fecha_iso(desde_texto)
            if hasta_texto:
                filtros["fecha_hasta"] = fecha_iso(hasta_texto)
            if (desde_texto and not hasta_texto) or (hasta_texto and not desde_texto):
                raise ValueError("Indique ambas fechas del rango.")
            if filtros.get("fecha_desde") and filtros.get("fecha_hasta"):
                if filtros["fecha_desde"] > filtros["fecha_hasta"]:
                    raise ValueError("La fecha desde no puede ser posterior a la fecha hasta.")
            categoria_id = self.categoria_por_nombre.get(self.filtro_categoria.get())
            if categoria_id:
                filtros["categoria_id"] = categoria_id
            if self.filtro_estado.get() not in ("", "Todos"):
                filtros["estado"] = self.filtro_estado.get()
            gastos = database.gastos_listar(filtros)
            self.tabla.delete(*self.tabla.get_children())
            for gasto in gastos:
                self.tabla.insert(
                    "", "end", iid=str(gasto["id"]),
                    values=(
                        fecha_pantalla(gasto["fecha"]), gasto["categoria"] or "",
                        gasto["concepto"], gasto["proveedor"] or "",
                        formatear_moneda(gasto["monto"]), gasto["estado"],
                    ),
                )
            self._actualizar_boton_pagado()
        except ValueError as error:
            messagebox.showerror("Filtro no válido", str(error))
        except database.ErrorBaseDatos as error:
            messagebox.showerror("Error de gastos", str(error))

    def _seleccionado(self) -> dict[str, Any] | None:
        seleccion = self.tabla.selection()
        if not seleccion:
            messagebox.showwarning("Selección requerida", "Seleccione un gasto primero.")
            return None
        try:
            return next(g for g in database.gastos_listar()
                        if g["id"] == int(seleccion[0]))
        except StopIteration:
            messagebox.showerror("Error", "El gasto seleccionado ya no existe.")
        except database.ErrorBaseDatos as error:
            messagebox.showerror("Error", str(error))
        return None

    def _actualizar_boton_pagado(self) -> None:
        seleccion = self.tabla.selection()
        habilitado = False
        if seleccion:
            try:
                gasto = next(
                    (g for g in database.gastos_listar() if g["id"] == int(seleccion[0])),
                    None,
                )
                habilitado = bool(gasto and gasto["estado"] == "pendiente")
            except database.ErrorBaseDatos as error:
                self.estado(f"Error al consultar gasto: {error}")
        self.boton_pagado.configure(state="normal" if habilitado else "disabled")

    def _nuevo(self) -> None:
        self._formulario()

    def _editar(self) -> None:
        gasto = self._seleccionado()
        if gasto:
            self._formulario(gasto)

    def _formulario(self, gasto: dict[str, Any] | None = None) -> None:
        """Valida los campos y conserva la fecha de pago según el estado elegido."""
        if not self.categorias:
            messagebox.showerror(
                "Categoría requerida", "Agregue al menos una categoría de gasto."
            )
            return
        ventana = tk.Toplevel(self)
        ventana.title("Editar gasto" if gasto else "Nuevo gasto")
        ventana.transient(self.winfo_toplevel())
        ventana.grab_set()
        marco = ttk.Frame(ventana, padding=14)
        marco.pack(fill="both", expand=True)
        ttk.Label(marco, text="Fecha (dd/mm/aaaa)").grid(row=0, column=0, sticky="w", pady=4)
        entrada_fecha = ttk.Entry(marco, width=25)
        entrada_fecha.grid(row=0, column=1, sticky="ew", pady=4)
        entrada_fecha.insert(
            0, fecha_pantalla(gasto["fecha"]) if gasto else fecha_pantalla(fecha_hoy_iso())
        )
        ttk.Label(marco, text="Categoría").grid(row=1, column=0, sticky="w", pady=4)
        categorias_nombre_id = {c["nombre"]: c["id"] for c in self.categorias}
        combo_categoria = ttk.Combobox(
            marco, state="readonly", values=list(categorias_nombre_id), width=35
        )
        combo_categoria.grid(row=1, column=1, sticky="ew", pady=4)
        if gasto:
            combo_categoria.set(gasto["categoria"] or "")
        else:
            combo_categoria.current(0)
        ttk.Label(marco, text="Concepto").grid(row=2, column=0, sticky="w", pady=4)
        entrada_concepto = ttk.Entry(marco, width=42)
        entrada_concepto.grid(row=2, column=1, sticky="ew", pady=4)
        if gasto:
            entrada_concepto.insert(0, gasto["concepto"])
        ttk.Label(marco, text="Monto").grid(row=3, column=0, sticky="w", pady=4)
        entrada_monto = ttk.Entry(marco, width=25)
        entrada_monto.grid(row=3, column=1, sticky="ew", pady=4)
        if gasto:
            entrada_monto.insert(0, str(gasto["monto"]))
        ttk.Label(marco, text="Proveedor (opcional)").grid(
            row=4, column=0, sticky="w", pady=4
        )
        proveedores_nombre_id = {p["nombre"]: p["id"] for p in self.proveedores}
        combo_proveedor = ttk.Combobox(
            marco, state="readonly", values=("", *proveedores_nombre_id), width=35
        )
        combo_proveedor.grid(row=4, column=1, sticky="ew", pady=4)
        if gasto and gasto.get("proveedor"):
            combo_proveedor.set(gasto["proveedor"])
        else:
            combo_proveedor.set("")
        ttk.Label(marco, text="Estado").grid(row=5, column=0, sticky="w", pady=4)
        combo_estado = ttk.Combobox(
            marco, state="readonly", values=("pagado", "pendiente"), width=20
        )
        combo_estado.grid(row=5, column=1, sticky="ew", pady=4)
        combo_estado.set(gasto["estado"] if gasto else "pagado")
        ttk.Label(marco, text="Notas").grid(row=6, column=0, sticky="w", pady=4)
        entrada_notas = ttk.Entry(marco, width=42)
        entrada_notas.grid(row=6, column=1, sticky="ew", pady=4)
        if gasto:
            entrada_notas.insert(0, gasto.get("notas") or "")
        marco.columnconfigure(1, weight=1)

        def guardar() -> None:
            try:
                fecha = fecha_iso(entrada_fecha.get())
                categoria_id = categorias_nombre_id.get(combo_categoria.get())
                if categoria_id is None:
                    raise ValueError("Seleccione una categoría.")
                concepto = texto_obligatorio(entrada_concepto.get(), "Concepto")
                monto = numero_positivo(entrada_monto.get(), "Monto", permitir_cero=False)
                proveedor_id = proveedores_nombre_id.get(combo_proveedor.get())
                estado = combo_estado.get()
                fecha_pago = (
                    fecha_hoy_iso() if estado == "pagado"
                    and (not gasto or gasto["estado"] != "pagado")
                    else gasto.get("fecha_pago") if gasto and estado == "pagado"
                    else fecha if estado == "pagado" else None
                )
                datos = (
                    fecha, categoria_id, concepto, monto, proveedor_id, estado,
                    fecha_pago, entrada_notas.get().strip(),
                )
                if gasto:
                    database.gastos_actualizar(gasto["id"], *datos)
                else:
                    database.gastos_insertar(*datos)
                ventana.destroy()
                self.actualizar()
                self.estado("Gasto guardado correctamente")
                messagebox.showinfo("Éxito", "El gasto se guardó correctamente.")
            except ValueError as error:
                messagebox.showerror("Dato no válido", str(error), parent=ventana)
            except database.ErrorBaseDatos as error:
                messagebox.showerror("Error", str(error), parent=ventana)

        botones = ttk.Frame(marco)
        botones.grid(row=7, column=0, columnspan=2, pady=(10, 0))
        ttk.Button(botones, text="Guardar", command=guardar).pack(side="left", padx=4)
        ttk.Button(botones, text="Cancelar", command=ventana.destroy).pack(side="left", padx=4)
        ventana.wait_window()

    def _marcar_pagado(self) -> None:
        """Registra el pago de un gasto pendiente con la fecha actual."""
        gasto = self._seleccionado()
        if not gasto or gasto["estado"] != "pendiente":
            return
        if messagebox.askyesno("Confirmar", "¿Marcar este gasto como pagado?"):
            try:
                database.gastos_marcar_pagado(gasto["id"])
                self.actualizar()
                self.estado("Gasto marcado como pagado")
                messagebox.showinfo("Éxito", "El gasto se marcó como pagado.")
            except (ValueError, database.ErrorBaseDatos) as error:
                messagebox.showerror("Error", str(error))

    def _eliminar(self) -> None:
        gasto = self._seleccionado()
        if not gasto:
            return
        if messagebox.askyesno("Confirmar eliminación", "¿Eliminar el gasto seleccionado?"):
            try:
                database.gastos_eliminar(gasto["id"])
                self.actualizar()
                self.estado("Gasto eliminado")
                messagebox.showinfo("Éxito", "El gasto se eliminó correctamente.")
            except database.ErrorBaseDatos as error:
                messagebox.showerror("Error", str(error))

    def _nueva_categoria(self) -> None:
        self._formulario_categoria()

    def _editar_categoria(self) -> None:
        seleccion = self.tabla_categorias.selection()
        if not seleccion:
            messagebox.showwarning("Selección requerida", "Seleccione una categoría.")
            return
        self._formulario_categoria({
            "id": int(seleccion[0]),
            "nombre": self.tabla_categorias.item(seleccion[0])["values"][0],
        })

    def _formulario_categoria(self, categoria: dict[str, Any] | None = None) -> None:
        ventana = tk.Toplevel(self)
        ventana.title("Editar categoría" if categoria else "Nueva categoría")
        ventana.transient(self.winfo_toplevel())
        ventana.grab_set()
        marco = ttk.Frame(ventana, padding=12)
        marco.pack(fill="both", expand=True)
        ttk.Label(marco, text="Nombre").grid(row=0, column=0, padx=4, pady=4)
        entrada = ttk.Entry(marco, width=32)
        entrada.grid(row=0, column=1, padx=4, pady=4)
        if categoria:
            entrada.insert(0, categoria["nombre"])

        def guardar() -> None:
            try:
                nombre = texto_obligatorio(entrada.get(), "Nombre")
                if categoria:
                    database.categorias_gasto_actualizar(categoria["id"], nombre)
                else:
                    database.categorias_gasto_insertar(nombre)
                ventana.destroy()
                self.actualizar()
                self.estado("Categoría de gasto guardada")
                messagebox.showinfo("Éxito", "La categoría se guardó correctamente.")
            except ValueError as error:
                messagebox.showerror("Dato no válido", str(error), parent=ventana)
            except database.ErrorBaseDatos as error:
                messagebox.showerror("Error", str(error), parent=ventana)

        ttk.Button(marco, text="Guardar", command=guardar).grid(
            row=1, column=0, columnspan=2, pady=6
        )
        ventana.wait_window()

    def _eliminar_categoria(self) -> None:
        seleccion = self.tabla_categorias.selection()
        if not seleccion:
            messagebox.showwarning("Selección requerida", "Seleccione una categoría.")
            return
        categoria_id = int(seleccion[0])
        if not messagebox.askyesno(
            "Confirmar eliminación",
            "¿Eliminar la categoría? Solo se puede eliminar si no tiene gastos asociados.",
        ):
            return
        try:
            database.categorias_gasto_eliminar(categoria_id)
            self.actualizar()
            self.estado("Categoría de gasto eliminada")
            messagebox.showinfo("Éxito", "La categoría se eliminó correctamente.")
        except ValueError as error:
            messagebox.showerror("No se pudo eliminar", str(error))
        except database.ErrorBaseDatos as error:
            messagebox.showerror("Error", str(error))
