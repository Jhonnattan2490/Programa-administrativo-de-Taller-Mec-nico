"""Estilos compartidos de la interfaz del taller."""

import tkinter as tk
from tkinter import ttk


def aplicar_estilos(ventana: tk.Tk) -> None:
    """Aplica una paleta consistente a los controles ttk de la aplicación."""
    estilo = ttk.Style(ventana)
    if "clam" in estilo.theme_names():
        estilo.theme_use("clam")

    fondo = "#f3f6fa"
    azul = "#2457a6"
    estilo.configure(".", font=("TkDefaultFont", 10))
    estilo.configure("TFrame", background=fondo)
    estilo.configure("TLabel", background=fondo, foreground="#1f2937")
    estilo.configure("TLabelframe", background=fondo, bordercolor="#cbd5e1")
    estilo.configure(
        "TLabelframe.Label", background=fondo, foreground="#334155",
        font=("TkDefaultFont", 10, "bold"),
    )
    estilo.configure(
        "TNotebook", background="#dce4ef", borderwidth=0, tabmargins=(3, 4, 3, 0)
    )
    estilo.configure(
        "TNotebook.Tab", background="#e5eaf1", foreground="#334155",
        borderwidth=2, relief="raised", padding=(13, 8),
    )
    estilo.map(
        "TNotebook.Tab",
        background=[("selected", "#ffffff"), ("active", "#f8fafc")],
        foreground=[("selected", azul), ("active", azul)],
        relief=[("selected", "raised")],
        bordercolor=[("selected", azul), ("active", "#94a3b8")],
    )
    estilo.configure(
        "TButton", background=azul, foreground="#ffffff", borderwidth=1,
        relief="raised", padding=(10, 6), bordercolor="#1e4788",
        lightcolor="#3b72c4", darkcolor="#193e78",
    )
    estilo.map(
        "TButton",
        background=[
            ("disabled", "#cbd5e1"), ("pressed", "#193e78"),
            ("active", "#3472c9"),
        ],
        foreground=[("disabled", "#64748b"), ("!disabled", "#ffffff")],
        relief=[("pressed", "sunken"), ("!pressed", "raised")],
    )
    estilo.configure(
        "Treeview", background="#ffffff", fieldbackground="#ffffff",
        foreground="#1f2937", rowheight=27,
    )
    estilo.configure(
        "Treeview.Heading", background="#e5eaf1", foreground="#1f2937",
        font=("TkDefaultFont", 10, "bold"), padding=(6, 6),
    )
    estilo.map(
        "Treeview", background=[("selected", "#cfe0fb")],
        foreground=[("selected", "#173b70")],
    )
    ventana.configure(background=fondo)
