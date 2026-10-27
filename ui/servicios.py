"""Catálogo de servicios del taller."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

import database
from utils.helpers import formatear_moneda
from utils.validaciones import numero_positivo, porcentaje_valido, texto_obligatorio


class Servicios(ttk.Frame):
    """Mantiene el catálogo de servicios y sus porcentajes sugeridos."""

    def __init__(self, master: tk.Misc, estado: Callable[[str], None]) -> None:
        super().__init__(master, padding=10)
        self.estado = estado
        barra = ttk.Frame(self)
        barra.pack(fill="x", pady=(0, 8))
        ttk.Button(barra, text="Nuevo", command=self._nuevo).pack(side="left", padx=4)
        ttk.Button(barra, text="Editar", command=self._editar).pack(side="left", padx=4)
        ttk.Button(barra, text="Eliminar", command=self._eliminar).pack(side="left", padx=4)
        columnas = ("nombre", "categoria", "descripcion", "precio", "porcentaje")
        marco_tabla = ttk.Frame(self)
        marco_tabla.pack(fill="both", expand=True)
        self.tabla = ttk.Treeview(
            marco_tabla, columns=columnas, show="headings", selectmode="browse"
        )
        encabezados = ("Nombre", "Categoría", "Descripción", "Precio cliente", "% predeterminado")
        anchos = (180, 140, 300, 130, 150)
        for columna, encabezado, ancho in zip(columnas, encabezados, anchos):
            self.tabla.heading(columna, text=encabezado)
            self.tabla.column(columna, width=ancho, minwidth=70)
        self._agregar_scrollbars()
        self.actualizar()

    def _agregar_scrollbars(self) -> None:
        marco = self.tabla.master
        vertical = ttk.Scrollbar(marco, orient="vertical", command=self.tabla.yview)
        horizontal = ttk.Scrollbar(marco, orient="horizontal", command=self.tabla.xview)
        self.tabla.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        vertical.pack(side="right", fill="y")
        horizontal.pack(side="bottom", fill="x")
        self.tabla.pack(side="left", fill="both", expand=True)

    def actualizar(self) -> None:
        """Recarga servicios y formatea precios para la tabla."""
        try:
            filas = database.servicios_listar()
            self.tabla.delete(*self.tabla.get_children())
            for fila in filas:
                self.tabla.insert(
                    "", "end", iid=str(fila["id"]),
                    values=(fila["nombre"], fila["categoria"] or "",
                            fila["descripcion"] or "", formatear_moneda(fila["precio_cliente"]),
                            f'{fila["porcentaje_default"]:g}%'),
                )
        except database.ErrorBaseDatos as error:
            messagebox.showerror("Error", str(error))

    def _nuevo(self) -> None:
        self._formulario()

    def _editar(self) -> None:
        seleccionado = self._seleccionado()
        if seleccionado is None:
            return
        try:
            servicio = next(s for s in database.servicios_listar() if s["id"] == int(seleccionado))
        except (database.ErrorBaseDatos, StopIteration) as error:
            messagebox.showerror("Error", str(error))
            return
        self._formulario(servicio)

    def _formulario(self, servicio: dict | None = None) -> None:
        """Valida precio y porcentaje antes de guardar el servicio."""
        ventana = tk.Toplevel(self)
        ventana.title("Editar servicio" if servicio else "Nuevo servicio")
        ventana.transient(self.winfo_toplevel())
        ventana.grab_set()
        marco = ttk.Frame(ventana, padding=14)
        marco.pack(fill="both", expand=True)
        entradas: dict[str, tk.Widget] = {}
        definiciones = (
            ("Nombre", servicio["nombre"] if servicio else ""),
            ("Categoría", servicio["categoria"] if servicio else ""),
            ("Descripción", servicio["descripcion"] if servicio else ""),
            ("Precio cliente", str(servicio["precio_cliente"]) if servicio else "0"),
            ("Porcentaje predeterminado", str(servicio["porcentaje_default"]) if servicio else "0"),
        )
        for fila, (etiqueta, valor) in enumerate(definiciones):
            ttk.Label(marco, text=etiqueta).grid(row=fila, column=0, sticky="w", pady=4)
            campo = ttk.Entry(marco, width=40)
            campo.insert(0, valor or "")
            campo.grid(row=fila, column=1, sticky="ew", pady=4)
            entradas[etiqueta] = campo
        marco.columnconfigure(1, weight=1)

        def guardar() -> None:
            try:
                datos = (
                    texto_obligatorio(entradas["Nombre"].get(), "Nombre"),
                    entradas["Categoría"].get().strip(),
                    entradas["Descripción"].get().strip(),
                    numero_positivo(entradas["Precio cliente"].get(), "Precio cliente"),
                    porcentaje_valido(entradas["Porcentaje predeterminado"].get()),
                )
                if servicio:
                    database.servicios_actualizar(servicio["id"], *datos)
                else:
                    database.servicios_insertar(*datos)
                ventana.destroy()
                self.actualizar()
                self.estado("Servicio guardado correctamente")
                messagebox.showinfo("Éxito", "El servicio se guardó correctamente.")
            except ValueError as error:
                messagebox.showerror("Dato no válido", str(error), parent=ventana)
            except database.ErrorBaseDatos as error:
                messagebox.showerror("Error", str(error), parent=ventana)

        ttk.Button(marco, text="Guardar", command=guardar).grid(
            row=len(definiciones), column=0, columnspan=2, pady=(10, 0)
        )
        ventana.wait_window()

    def _eliminar(self) -> None:
        seleccionado = self._seleccionado()
        if seleccionado is None:
            return
        if messagebox.askyesno("Confirmar", "¿Desea eliminar el servicio seleccionado?"):
            try:
                database.servicios_eliminar(int(seleccionado))
                self.actualizar()
                self.estado("Servicio eliminado")
                messagebox.showinfo("Éxito", "El servicio se eliminó correctamente.")
            except database.ErrorBaseDatos as error:
                messagebox.showerror("Error", str(error))

    def _seleccionado(self) -> str | None:
        seleccion = self.tabla.selection()
        if not seleccion:
            messagebox.showwarning("Selección requerida", "Seleccione un registro primero.")
            return None
        return seleccion[0]
