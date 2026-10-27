"""Catálogo de productos y categorías."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

import database
from utils.helpers import formatear_moneda
from utils.validaciones import (
    numero_entero_positivo,
    numero_positivo,
    texto_obligatorio,
)


class Inventario(ttk.Frame):
    """Gestiona productos, categorías y alertas por nivel de existencias."""

    def __init__(self, master: tk.Misc, estado: Callable[[str], None]) -> None:
        super().__init__(master, padding=10)
        self.estado = estado
        self.pestanas = ttk.Notebook(self)
        self.pestanas.pack(fill="both", expand=True)
        self.pestana_productos = ttk.Frame(self.pestanas, padding=8)
        self.pestana_categorias = ttk.Frame(self.pestanas, padding=8)
        self.pestanas.add(self.pestana_productos, text="Productos")
        self.pestanas.add(self.pestana_categorias, text="Categorías")
        self._crear_productos()
        self._crear_categorias()
        self.actualizar_productos()
        self.actualizar_categorias()

    def actualizar(self) -> None:
        """Recarga productos y categorías al abrir la pestaña de inventario."""
        self.actualizar_productos()
        self.actualizar_categorias()

    def _crear_productos(self) -> None:
        barra = ttk.Frame(self.pestana_productos)
        barra.pack(fill="x", pady=(0, 8))
        ttk.Label(barra, text="Buscar por nombre:").pack(side="left")
        self.busqueda = tk.StringVar()
        entrada = ttk.Entry(barra, textvariable=self.busqueda, width=32)
        entrada.pack(side="left", padx=6)
        entrada.bind(
            "<KeyRelease>",
            lambda evento: self.actualizar_productos() if evento.widget is entrada else None,
        )
        ttk.Button(barra, text="Nuevo", command=self._nuevo_producto).pack(side="left", padx=4)
        ttk.Button(barra, text="Editar", command=self._editar_producto).pack(side="left", padx=4)
        ttk.Button(barra, text="Eliminar", command=self._eliminar_producto).pack(side="left", padx=4)

        columnas = ("nombre", "categoria", "precio_compra", "precio_venta",
                    "stock", "stock_minimo", "alerta")
        self.tabla_productos = ttk.Treeview(
            self.pestana_productos, columns=columnas, show="headings", selectmode="browse"
        )
        encabezados = {
            "nombre": "Nombre", "categoria": "Categoría",
            "precio_compra": "Precio compra", "precio_venta": "Precio venta",
            "stock": "Stock", "stock_minimo": "Stock mínimo", "alerta": "Alerta",
        }
        anchos = {"nombre": 190, "categoria": 140, "precio_compra": 130,
                  "precio_venta": 130, "stock": 80, "stock_minimo": 110, "alerta": 90}
        for columna in columnas:
            self.tabla_productos.heading(columna, text=encabezados[columna])
            self.tabla_productos.column(columna, width=anchos[columna], minwidth=70)
        self.tabla_productos.tag_configure("bajo", background="#f4cccc")
        self._agregar_scrollbars(self.pestana_productos, self.tabla_productos)

    def _crear_categorias(self) -> None:
        barra = ttk.Frame(self.pestana_categorias)
        barra.pack(fill="x", pady=(0, 8))
        ttk.Button(barra, text="Nueva categoría", command=self._nueva_categoria).pack(side="left", padx=4)
        ttk.Button(barra, text="Editar", command=self._editar_categoria).pack(side="left", padx=4)
        ttk.Button(barra, text="Eliminar", command=self._eliminar_categoria).pack(side="left", padx=4)
        self.tabla_categorias = ttk.Treeview(
            self.pestana_categorias, columns=("nombre",), show="headings", selectmode="browse"
        )
        self.tabla_categorias.heading("nombre", text="Nombre")
        self.tabla_categorias.column("nombre", width=300)
        self._agregar_scrollbars(self.pestana_categorias, self.tabla_categorias)

    @staticmethod
    def _agregar_scrollbars(contenedor: ttk.Frame, tabla: ttk.Treeview) -> None:
        """Empaqueta tabla y barras como hijos del mismo contenedor."""
        vertical = ttk.Scrollbar(contenedor, orient="vertical", command=tabla.yview)
        horizontal = ttk.Scrollbar(contenedor, orient="horizontal", command=tabla.xview)
        tabla.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        vertical.pack(side="right", fill="y")
        horizontal.pack(side="bottom", fill="x")
        tabla.pack(side="left", fill="both", expand=True)

    def actualizar_productos(self) -> None:
        """Aplica la búsqueda y marca las filas con stock en el mínimo o menor."""
        try:
            filas = database.productos_listar(self.busqueda.get())
            self.tabla_productos.delete(*self.tabla_productos.get_children())
            for fila in filas:
                bajo = fila["stock"] <= fila["stock_minimo"]
                self.tabla_productos.insert(
                    "", "end", iid=str(fila["id"]),
                    values=(fila["nombre"], fila["categoria"] or "",
                            formatear_moneda(fila["precio_compra"]),
                            formatear_moneda(fila["precio_venta"]), fila["stock"],
                            fila["stock_minimo"], "Stock bajo" if bajo else ""),
                    tags=("bajo",) if bajo else (),
                )
        except database.ErrorBaseDatos as error:
            messagebox.showerror("Error", str(error))

    def actualizar_categorias(self) -> None:
        try:
            filas = database.categorias_listar()
            self.tabla_categorias.delete(*self.tabla_categorias.get_children())
            for fila in filas:
                self.tabla_categorias.insert(
                    "", "end", iid=str(fila["id"]), values=(fila["nombre"],)
                )
        except database.ErrorBaseDatos as error:
            messagebox.showerror("Error", str(error))

    def _nuevo_producto(self) -> None:
        self._formulario_producto()

    def _editar_producto(self) -> None:
        fila = self._seleccionado(self.tabla_productos)
        if fila is None:
            return
        try:
            producto = next(p for p in database.productos_listar()
                            if p["id"] == int(fila))
        except (database.ErrorBaseDatos, StopIteration) as error:
            messagebox.showerror("Error", str(error))
            return
        self._formulario_producto(producto)

    def _formulario_producto(self, producto: dict | None = None) -> None:
        """Valida los campos numéricos antes de crear o actualizar el producto."""
        ventana = tk.Toplevel(self)
        ventana.title("Editar producto" if producto else "Nuevo producto")
        ventana.transient(self.winfo_toplevel())
        ventana.grab_set()
        marco = ttk.Frame(ventana, padding=14)
        marco.pack(fill="both", expand=True)
        try:
            categorias = database.categorias_listar()
        except database.ErrorBaseDatos as error:
            ventana.destroy()
            messagebox.showerror("Error", str(error))
            return
        por_nombre = {c["nombre"]: c["id"] for c in categorias}
        campos = {}
        valores = {
            "Nombre": producto["nombre"] if producto else "",
            "Categoría": producto["categoria"] if producto else "",
            "Precio de compra": str(producto["precio_compra"]) if producto else "0",
            "Precio de venta": str(producto["precio_venta"]) if producto else "0",
            "Stock": str(producto["stock"]) if producto else "0",
            "Stock mínimo": str(producto["stock_minimo"]) if producto else "0",
        }
        for indice, (etiqueta, valor) in enumerate(valores.items()):
            ttk.Label(marco, text=etiqueta).grid(row=indice, column=0, sticky="w", pady=4)
            if etiqueta == "Categoría":
                campo = ttk.Combobox(marco, values=[""] + list(por_nombre), state="readonly")
                campo.set(valor)
            else:
                campo = ttk.Entry(marco)
                campo.insert(0, valor)
            campo.grid(row=indice, column=1, sticky="ew", pady=4)
            campos[etiqueta] = campo
        marco.columnconfigure(1, weight=1)

        def guardar() -> None:
            try:
                nombre = texto_obligatorio(campos["Nombre"].get(), "Nombre")
                compra = numero_positivo(campos["Precio de compra"].get(), "Precio de compra")
                venta = numero_positivo(campos["Precio de venta"].get(), "Precio de venta")
                stock = numero_entero_positivo(campos["Stock"].get(), "Stock")
                minimo = numero_entero_positivo(campos["Stock mínimo"].get(), "Stock mínimo")
                categoria = por_nombre.get(campos["Categoría"].get())
                if producto:
                    database.productos_actualizar(
                        producto["id"], nombre, categoria, compra, venta, stock, minimo
                    )
                else:
                    database.productos_insertar(nombre, categoria, compra, venta, stock, minimo)
                ventana.destroy()
                self.actualizar_productos()
                self.estado("Producto guardado correctamente")
                messagebox.showinfo("Éxito", "El producto se guardó correctamente.")
            except ValueError as error:
                messagebox.showerror("Dato no válido", str(error), parent=ventana)
            except database.ErrorBaseDatos as error:
                messagebox.showerror("Error", str(error), parent=ventana)

        ttk.Button(marco, text="Guardar", command=guardar).grid(
            row=len(campos), column=0, columnspan=2, pady=(10, 0)
        )
        ventana.bind(
            "<Return>", lambda evento: guardar() if evento.keysym == "Return" else None
        )
        ventana.wait_window()

    def _eliminar_producto(self) -> None:
        """Elimina el producto seleccionado después de pedir confirmación."""
        seleccionado = self._seleccionado(self.tabla_productos)
        if seleccionado is None:
            return
        if messagebox.askyesno("Confirmar", "¿Desea eliminar el producto seleccionado?"):
            try:
                database.productos_eliminar(int(seleccionado))
                self.actualizar_productos()
                self.estado("Producto eliminado")
                messagebox.showinfo("Éxito", "El producto se eliminó correctamente.")
            except database.ErrorBaseDatos as error:
                messagebox.showerror("Error", str(error))

    def _nueva_categoria(self) -> None:
        self._formulario_categoria()

    def _editar_categoria(self) -> None:
        seleccionado = self._seleccionado(self.tabla_categorias)
        if seleccionado is None:
            return
        self._formulario_categoria(
            {"id": int(seleccionado), "nombre": self.tabla_categorias.item(seleccionado)["values"][0]}
        )

    def _formulario_categoria(self, categoria: dict | None = None) -> None:
        ventana = tk.Toplevel(self)
        ventana.title("Categoría")
        ventana.transient(self.winfo_toplevel())
        ventana.grab_set()
        marco = ttk.Frame(ventana, padding=14)
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
                    database.categorias_actualizar(categoria["id"], nombre)
                else:
                    database.categorias_insertar(nombre)
                ventana.destroy()
                self.actualizar_categorias()
                self.actualizar_productos()
                self.estado("Categoría guardada correctamente")
                messagebox.showinfo("Éxito", "La categoría se guardó correctamente.")
            except ValueError as error:
                messagebox.showerror("Dato no válido", str(error), parent=ventana)
            except database.ErrorBaseDatos as error:
                messagebox.showerror("Error", str(error), parent=ventana)

        ttk.Button(marco, text="Guardar", command=guardar).grid(
            row=1, column=0, columnspan=2, pady=8
        )
        ventana.wait_window()

    def _eliminar_categoria(self) -> None:
        seleccionado = self._seleccionado(self.tabla_categorias)
        if seleccionado is None:
            return
        if messagebox.askyesno("Confirmar", "¿Desea eliminar la categoría seleccionada?"):
            try:
                database.categorias_eliminar(int(seleccionado))
                self.actualizar_categorias()
                self.actualizar_productos()
                self.estado("Categoría eliminada")
                messagebox.showinfo("Éxito", "La categoría se eliminó correctamente.")
            except database.ErrorBaseDatos as error:
                messagebox.showerror("Error", str(error))

    @staticmethod
    def _seleccionado(tabla: ttk.Treeview) -> str | None:
        seleccion = tabla.selection()
        if not seleccion:
            messagebox.showwarning("Selección requerida", "Seleccione un registro primero.")
            return None
        return seleccion[0]
