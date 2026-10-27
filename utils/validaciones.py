"""Validaciones reutilizables para formularios."""

from tkinter import messagebox


def texto_obligatorio(valor: str, etiqueta: str) -> str:
    """Recorta y valida que un campo de texto no esté vacío."""
    texto = valor.strip()
    if not texto:
        raise ValueError(f"El campo {etiqueta} es obligatorio.")
    return texto


def numero_positivo(valor: str, etiqueta: str, permitir_cero: bool = True) -> float:
    """Interpreta números con coma decimal o punto de miles y rechaza negativos."""
    texto = valor.strip().replace(" ", "")
    try:
        if "," in texto:
            numero = float(texto.replace(".", "").replace(",", "."))
        elif texto.count(".") > 1 or (
            "." in texto
            and 1 <= len(texto.split(".", 1)[0]) <= 3
            and all(len(grupo) == 3 for grupo in texto.split(".")[1:])
        ):
            numero = float(texto.replace(".", ""))
        else:
            numero = float(texto)
    except ValueError as error:
        raise ValueError(f"{etiqueta} debe ser un número válido.") from error
    if numero < 0 or (not permitir_cero and numero == 0):
        requisito = "mayor que cero" if not permitir_cero else "positivo o cero"
        raise ValueError(f"{etiqueta} debe ser {requisito}.")
    return numero


def numero_entero_positivo(valor: str, etiqueta: str) -> int:
    """Comprueba que el número ingresado no tenga parte decimal."""
    numero = numero_positivo(valor, etiqueta)
    if not numero.is_integer():
        raise ValueError(f"{etiqueta} debe ser un número entero.")
    return int(numero)


def porcentaje_valido(valor: str, etiqueta: str = "Porcentaje") -> float:
    """Valida que el porcentaje se encuentre entre 0 y 100."""
    porcentaje = numero_positivo(valor, etiqueta)
    if porcentaje > 100:
        raise ValueError(f"{etiqueta} debe estar entre 0 y 100.")
    return porcentaje


def mostrar_error_validacion(error: ValueError) -> None:
    messagebox.showerror("Dato no válido", str(error))
