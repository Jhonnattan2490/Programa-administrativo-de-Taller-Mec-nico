"""Interfaz compartida para clientes y proveedores."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

import database
from utils.validaciones import texto_obligatorio


class CatalogoPersonas(ttk.Frame):
    """Interfaz común para clientes y proveedores."""

    entidad = ""
    titulo = ""

    def __init__(self, master: tk.Misc, estado: Callable[[str], None]) -> None:
        super().__init__(master, padding=10)
        self.estado = estado
        barra = ttk.Frame(self)
        barra.pack(fill="x", pady=(0, 8))
        ttk.Button(barra, text="Nuevo", command=self._nuevo).pack(side="left", padx=4)
        ttk.Button(barra, text="Editar", command=self._editar).pack(side="left", padx=4)
        ttk.Button(barra, text="Eliminar", command=self._eliminar).pack(side="left", padx=4)
        columnas = ("nombre", "telefono", "direccion", "email", "notas")
        marco = ttk.Frame(self)
        marco.pack(fill="both", expand=True)
        self.tabla = ttk.Treeview(
            marco, columns=columnas, show="headings", selectmode="browse"
        )
        for columna, encabezado, ancho in (
            ("nombre", "Nombre", 200), ("telefono", "Teléfono", 130),
            ("direccion", "Dirección", 240), ("email", "Correo electrónico", 200),
            ("notas", "Notas", 260),
        ):
            self.tabla.heading(columna, text=encabezado)
            self.tabla.column(columna, width=ancho, minwidth=80)
        vertical = ttk.Scrollbar(marco, orient="vertical", command=self.tabla.yview)
        horizontal = ttk.Scrollbar(marco, orient="horizontal", command=self.tabla.xview)
        self.tabla.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        vertical.pack(side="right", fill="y")
        horizontal.pack(side="bottom", fill="x")
        self.tabla.pack(side="left", fill="both", expand=True)
        self.actualizar()

    def _listar(self) -> list[dict]:
        return getattr(database, f"{self.entidad}_listar")()

    def _guardar(self, datos: tuple, persona_id: int | None = None) -> int:
        """Dirige la operación al CRUD correspondiente a la subclase."""
        if persona_id is None:
            return getattr(database, f"{self.entidad}_insertar")(*datos)
        return getattr(database, f"{self.entidad}_actualizar")(persona_id, *datos)

    def actualizar(self) -> None:
        try:
            filas = self._listar()
            self.tabla.delete(*self.tabla.get_children())
            for fila in filas:
                self.tabla.insert(
                    "", "end", iid=str(fila["id"]),
                    values=tuple(fila[campo] or "" for campo in
                                 ("nombre", "telefono", "direccion", "email", "notas")),
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
            persona = next(p for p in self._listar() if p["id"] == int(seleccionado))
        except (database.ErrorBaseDatos, StopIteration) as error:
            messagebox.showerror("Error", str(error))
            return
        self._formulario(persona)

    def _formulario(self, persona: dict | None = None) -> None:
        """Comparte validación y formulario para los datos de contacto."""
        ventana = tk.Toplevel(self)
        ventana.title(f"{'Editar' if persona else 'Nuevo'} {self.titulo.lower()}")
        ventana.transient(self.winfo_toplevel())
        ventana.grab_set()
        marco = ttk.Frame(ventana, padding=14)
        marco.pack(fill="both", expand=True)
        claves = ("Nombre", "Teléfono", "Dirección", "Correo electrónico", "Notas")
        nombres = ("nombre", "telefono", "direccion", "email", "notas")
        campos: list[ttk.Entry] = []
        for fila, (clave, nombre_campo) in enumerate(zip(claves, nombres)):
            ttk.Label(marco, text=clave).grid(row=fila, column=0, sticky="w", pady=4)
            entrada = ttk.Entry(marco, width=42)
            entrada.grid(row=fila, column=1, sticky="ew", pady=4)
            if persona:
                entrada.insert(0, persona[nombre_campo] or "")
            campos.append(entrada)
        marco.columnconfigure(1, weight=1)

        def guardar() -> None:
            try:
                datos = tuple(campo.get().strip() for campo in campos)
                datos = (texto_obligatorio(datos[0], "Nombre"), *datos[1:])
                self._guardar(datos, persona["id"] if persona else None)
                ventana.destroy()
                self.actualizar()
                self.estado(f"{self.titulo} guardado correctamente")
                messagebox.showinfo("Éxito", f"{self.titulo} guardado correctamente.")
            except ValueError as error:
                messagebox.showerror("Dato no válido", str(error), parent=ventana)
            except database.ErrorBaseDatos as error:
                messagebox.showerror("Error", str(error), parent=ventana)

        ttk.Button(marco, text="Guardar", command=guardar).grid(
            row=len(claves), column=0, columnspan=2, pady=(10, 0)
        )
        ventana.wait_window()

    def _eliminar(self) -> None:
        seleccionado = self._seleccionado()
        if seleccionado is None:
            return
        if messagebox.askyesno(
            "Confirmar", f"¿Desea eliminar el registro seleccionado de {self.titulo.lower()}?"
        ):
            try:
                getattr(database, f"{self.entidad}_eliminar")(int(seleccionado))
                self.actualizar()
                self.estado(f"{self.titulo} eliminado")
                messagebox.showinfo("Éxito", f"{self.titulo} eliminado correctamente.")
            except database.ErrorBaseDatos as error:
                messagebox.showerror("Error", str(error))

    def _seleccionado(self) -> str | None:
        seleccion = self.tabla.selection()
        if not seleccion:
            messagebox.showwarning("Selección requerida", "Seleccione un registro primero.")
            return None
        return seleccion[0]
