"""Administración de trabajadores."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

import database
from utils.validaciones import texto_obligatorio


class Trabajadores(ttk.Frame):
    """Administra trabajadores y usa baja lógica para conservar su historial."""

    def __init__(self, master: tk.Misc, estado: Callable[[str], None]) -> None:
        super().__init__(master, padding=10)
        self.estado = estado
        barra = ttk.Frame(self)
        barra.pack(fill="x", pady=(0, 8))
        ttk.Button(barra, text="Nuevo", command=self._nuevo).pack(side="left", padx=4)
        ttk.Button(barra, text="Editar", command=self._editar).pack(side="left", padx=4)
        ttk.Button(barra, text="Eliminar", command=self._eliminar).pack(side="left", padx=4)
        marco = ttk.Frame(self)
        marco.pack(fill="both", expand=True)
        self.tabla = ttk.Treeview(
            marco, columns=("cedula", "nombre", "cargo"), show="headings", selectmode="browse"
        )
        for columna, titulo, ancho in (
            ("cedula", "Cédula", 160), ("nombre", "Nombre", 260), ("cargo", "Cargo", 200)
        ):
            self.tabla.heading(columna, text=titulo)
            self.tabla.column(columna, width=ancho)
        vertical = ttk.Scrollbar(marco, orient="vertical", command=self.tabla.yview)
        horizontal = ttk.Scrollbar(marco, orient="horizontal", command=self.tabla.xview)
        self.tabla.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        vertical.pack(side="right", fill="y")
        horizontal.pack(side="bottom", fill="x")
        self.tabla.pack(side="left", fill="both", expand=True)
        self.actualizar()

    def actualizar(self) -> None:
        try:
            filas = database.trabajadores_listar()
            self.tabla.delete(*self.tabla.get_children())
            for fila in filas:
                self.tabla.insert(
                    "", "end", iid=str(fila["id"]),
                    values=(fila["cedula"], fila["nombre"], fila["cargo"]),
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
            trabajador = next(
                t for t in database.trabajadores_listar() if t["id"] == int(seleccionado)
            )
        except (database.ErrorBaseDatos, StopIteration) as error:
            messagebox.showerror("Error", str(error))
            return
        self._formulario(trabajador)

    def _formulario(self, trabajador: dict | None = None) -> None:
        ventana = tk.Toplevel(self)
        ventana.title("Editar trabajador" if trabajador else "Nuevo trabajador")
        ventana.transient(self.winfo_toplevel())
        ventana.grab_set()
        marco = ttk.Frame(ventana, padding=14)
        marco.pack(fill="both", expand=True)
        campos: dict[str, ttk.Entry] = {}
        for fila, clave in enumerate(("Cédula", "Nombre", "Cargo")):
            ttk.Label(marco, text=clave).grid(row=fila, column=0, sticky="w", pady=4)
            campo = ttk.Entry(marco, width=36)
            campo.grid(row=fila, column=1, sticky="ew", pady=4)
            campos[clave] = campo
        if trabajador:
            for campo, valor in zip(campos.values(), (
                trabajador["cedula"], trabajador["nombre"], trabajador["cargo"]
            )):
                campo.insert(0, valor)
        marco.columnconfigure(1, weight=1)

        def guardar() -> None:
            try:
                cedula = texto_obligatorio(campos["Cédula"].get(), "Cédula")
                nombre = texto_obligatorio(campos["Nombre"].get(), "Nombre")
                cargo = texto_obligatorio(campos["Cargo"].get(), "Cargo")
                if trabajador:
                    database.trabajadores_actualizar(trabajador["id"], cedula, nombre, cargo)
                else:
                    database.trabajadores_insertar(cedula, nombre, cargo)
                ventana.destroy()
                self.actualizar()
                self.estado("Trabajador guardado correctamente")
                messagebox.showinfo("Éxito", "El trabajador se guardó correctamente.")
            except ValueError as error:
                messagebox.showerror("Dato no válido", str(error), parent=ventana)
            except database.ErrorBaseDatos as error:
                messagebox.showerror("Error", str(error), parent=ventana)

        ttk.Button(marco, text="Guardar", command=guardar).grid(
            row=3, column=0, columnspan=2, pady=(10, 0)
        )
        ventana.wait_window()

    def _eliminar(self) -> None:
        """Desactiva al trabajador en lugar de borrar sus relaciones históricas."""
        seleccionado = self._seleccionado()
        if seleccionado is None:
            return
        if messagebox.askyesno(
            "Confirmar", "¿Desea desactivar el trabajador seleccionado?"
        ):
            try:
                database.trabajadores_eliminar(int(seleccionado))
                self.actualizar()
                self.estado("Trabajador desactivado")
                messagebox.showinfo("Éxito", "El trabajador se desactivó correctamente.")
            except database.ErrorBaseDatos as error:
                messagebox.showerror("Error", str(error))

    def _seleccionado(self) -> str | None:
        seleccion = self.tabla.selection()
        if not seleccion:
            messagebox.showwarning("Selección requerida", "Seleccione un registro primero.")
            return None
        return seleccion[0]
