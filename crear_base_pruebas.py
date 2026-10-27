"""Crea una base aislada con datos ficticios para probar la aplicación y sus PDF."""

import argparse
from datetime import date, timedelta
from pathlib import Path
import sqlite3


CARPETA_PROYECTO = Path(__file__).resolve().parent
RUTA_ESQUEMA = CARPETA_PROYECTO / "schema.sql"
RUTA_POR_DEFECTO = CARPETA_PROYECTO / "taller_pruebas.db"


def crear_base_pruebas(destino: Path, sobrescribir: bool = False) -> Path:
    """Crea un archivo SQLite de prueba sin modificar la base del taller."""
    if destino.exists() and not sobrescribir:
        raise FileExistsError(
            f"El archivo ya existe: {destino}. Use --sobrescribir para reemplazarlo."
        )
    if destino.exists():
        destino.unlink()

    destino.parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(destino)
    conexion.row_factory = sqlite3.Row
    with conexion:
        conexion.execute("PRAGMA foreign_keys = ON")
        conexion.executescript(RUTA_ESQUEMA.read_text(encoding="utf-8"))
        hoy = date.today()
        hace_dos_dias = (hoy - timedelta(days=2)).isoformat()
        hace_un_dia = (hoy - timedelta(days=1)).isoformat()
        hace_tres_dias = (hoy - timedelta(days=3)).isoformat()
        fecha_entrega = (hoy + timedelta(days=2)).isoformat()

        with conexion:
            conexion.execute(
                "UPDATE trabajadores SET nombre=?, cargo=? WHERE id=1",
                ("Carlos Ramírez", "Mecánico"),
            )
            conexion.execute(
                "UPDATE trabajadores SET nombre=?, cargo=? WHERE id=2",
                ("Andrés Torres", "Soldador"),
            )
            conexion.executemany(
                """INSERT INTO trabajadores (cedula, nombre, cargo, activo)
                   VALUES (?, ?, ?, 1)""",
                [
                    ("10000003", "María Gómez", "Administradora"),
                    ("10000004", "Luis Herrera", "Ayudante de taller"),
                ],
            )
            conexion.executemany(
                """INSERT INTO clientes (nombre, telefono, direccion, email, notas)
                   VALUES (?, ?, ?, ?, ?)""",
                [
                    ("Transportes El Camino", "3005550101", "Calle 12 # 8-20",
                     "contacto@elcamino.example", "Cliente frecuente (datos ficticios)."),
                    ("María Fernanda Rojas", "3005550102", "Carrera 7 # 15-30",
                     "maria.rojas@example", "Moto para mantenimiento preventivo."),
                    ("Construcciones del Norte", "3005550103", "Avenida 4 # 22-10",
                     "compras@norte.example", "Solicita cotización de soldadura."),
                ],
            )
            conexion.executemany(
                """INSERT INTO proveedores (nombre, telefono, direccion, email, notas)
                   VALUES (?, ?, ?, ?, ?)""",
                [
                    ("Repuestos La 14", "3005550201", "Calle 14 # 5-18",
                     "ventas@repuestos14.example", "Proveedor de repuestos (datos ficticios)."),
                    ("Suministros Industriales", "3005550202", "Carrera 9 # 30-45",
                     "pedidos@suministros.example", "Consumibles para soldadura."),
                ],
            )

            categorias = {
                fila["nombre"]: fila["id"]
                for fila in conexion.execute("SELECT id, nombre FROM categorias")
            }
            categorias_gasto = {
                fila["nombre"]: fila["id"]
                for fila in conexion.execute("SELECT id, nombre FROM categorias_gasto")
            }
            servicios = {
                fila["nombre"]: fila["id"]
                for fila in conexion.execute("SELECT id, nombre FROM servicios")
            }
            trabajadores = {
                fila["nombre"]: fila["id"]
                for fila in conexion.execute("SELECT id, nombre FROM trabajadores")
            }
            clientes = {
                fila["nombre"]: fila["id"]
                for fila in conexion.execute("SELECT id, nombre FROM clientes")
            }
            proveedores = {
                fila["nombre"]: fila["id"]
                for fila in conexion.execute("SELECT id, nombre FROM proveedores")
            }
            conexion.executemany(
                """INSERT INTO productos
                   (nombre, categoria_id, precio_compra, precio_venta, stock, stock_minimo)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                [
                    ("Electrodo 6013 1/8", categorias["Insumos"], 1800, 3000, 80, 15),
                    ("Disco de corte 4.5 pulgadas", categorias["Herramientas"], 2500, 4500, 35, 8),
                    ("Aceite para motor 1L", categorias["Repuestos"], 18000, 26000, 24, 5),
                    ("Kit de parches", categorias["Mecánica"], 3500, 7000, 4, 6),
                    ("Varilla de soldadura", categorias["Soldadura"], 5000, 8500, 40, 10),
                ],
            )

            producto_ids = {
                fila["nombre"]: fila["id"]
                for fila in conexion.execute("SELECT id, nombre FROM productos")
            }

            def agregar_documento(
                tipo: str, numero: int, fecha: str, cliente: str, estado: str,
                lineas: list[tuple[str, str, float, float]],
                campos: dict[str, str | None] | None = None,
            ) -> tuple[int, list[int]]:
                subtotal = sum(cantidad * precio for _, _, cantidad, precio in lineas)
                datos = {
                    "tipo": tipo,
                    "numero": numero,
                    "fecha_emision": fecha,
                    "cliente_id": clientes[cliente],
                    "subtotal": subtotal,
                    "total": subtotal,
                    "estado": estado,
                    **(campos or {}),
                }
                columnas = ", ".join(datos)
                marcadores = ", ".join("?" for _ in datos)
                cursor = conexion.execute(
                    f"INSERT INTO documentos ({columnas}) VALUES ({marcadores})",
                    tuple(datos.values()),
                )
                documento_id = int(cursor.lastrowid)
                detalle_ids = []
                for item_tipo, nombre, cantidad, precio in lineas:
                    item_id = (
                        producto_ids[nombre] if item_tipo == "producto" else servicios[nombre]
                    )
                    detalle = conexion.execute(
                        """INSERT INTO detalle_documentos
                           (documento_id, item_tipo, item_id, cantidad, precio_unitario, subtotal)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (documento_id, item_tipo, item_id, cantidad, precio, cantidad * precio),
                    )
                    detalle_ids.append(int(detalle.lastrowid))
                return documento_id, detalle_ids

            agregar_documento(
                "factura", 1, hoy.isoformat(), "Transportes El Camino", "pagada",
                [("producto", "Electrodo 6013 1/8", 5, 3000),
                 ("servicio", "Soldadura", 1, 50000)],
                {"notas": "Factura de prueba pagada."},
            )
            agregar_documento(
                "factura", 2, hace_un_dia, "María Fernanda Rojas", "emitida",
                [("producto", "Aceite para motor 1L", 2, 26000),
                 ("servicio", "Mecánica general", 1, 40000)],
                {"notas": "Factura de prueba pendiente de pago."},
            )
            cotizacion_id, _ = agregar_documento(
                "cotizacion", 1, hace_tres_dias, "Construcciones del Norte", "emitida",
                [("producto", "Disco de corte 4.5 pulgadas", 10, 4500),
                 ("servicio", "Soldadura", 2, 50000)],
                {"notas": "Cotización de prueba."},
            )
            _, detalles_ot = agregar_documento(
                "orden_trabajo", 1, hace_dos_dias, "Construcciones del Norte", "aprobada",
                [("servicio", "Soldadura", 2, 50000),
                 ("producto", "Electrodo 6013 1/8", 8, 3000)],
                {"falla_reportada": "Soporte lateral fisurado.",
                 "documento_origen_id": cotizacion_id},
            )
            conexion.execute(
                """INSERT INTO detalle_trabajadores (detalle_id, trabajador_id, porcentaje)
                   VALUES (?, ?, ?)""",
                (detalles_ot[0], trabajadores["Andrés Torres"], 40),
            )
            _, detalles_os = agregar_documento(
                "orden_servicio", 1, hoy.isoformat(), "María Fernanda Rojas", "emitida",
                [("servicio", "Mecánica general", 1, 40000),
                 ("producto", "Aceite para motor 1L", 1, 26000),
                 ("servicio", "Engrase", 1, 15000)],
                {
                    "fecha_inicio": hoy.isoformat(),
                    "fecha_entrega": fecha_entrega,
                    "equipo": "Motocicleta",
                    "placa": "ABC-123",
                    "serial_ot": "OT-2026-001",
                    "tiempo_estimado": "2 días",
                    "falla_reportada": "Ruido en el motor y requiere mantenimiento.",
                    "causa_falla": "Desgaste normal y lubricación insuficiente.",
                    "trabajos_ejecutados": "Revisión general, cambio de aceite y engrase.",
                    "recomendaciones": "Realizar mantenimiento preventivo cada tres meses.",
                },
            )
            asignaciones = []
            for detalle_id, trabajador_nombre, porcentaje in (
                (detalles_os[0], "Carlos Ramírez", 35),
                (detalles_os[0], "Andrés Torres", 15),
                (detalles_os[2], "Carlos Ramírez", 30),
            ):
                cursor = conexion.execute(
                    """INSERT INTO detalle_trabajadores (detalle_id, trabajador_id, porcentaje)
                       VALUES (?, ?, ?)""",
                    (detalle_id, trabajadores[trabajador_nombre], porcentaje),
                )
                asignaciones.append((int(cursor.lastrowid), trabajador_nombre, porcentaje))

            fecha_comision = hoy.isoformat()
            total_liquidado = 40000 * 0.35
            cursor = conexion.execute(
                """INSERT INTO desprendibles
                   (numero, trabajador_id, fecha_emision, periodo_inicio, periodo_fin, total, estado)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (1, trabajadores["Carlos Ramírez"], fecha_comision,
                 hace_tres_dias, hoy.isoformat(), total_liquidado, "pagado"),
            )
            desprendible_id = int(cursor.lastrowid)
            for detalle_trabajador_id, nombre, porcentaje in asignaciones:
                base_comision = 40000 if detalle_trabajador_id != asignaciones[2][0] else 15000
                monto = base_comision * porcentaje / 100
                esta_pagada = nombre == "Carlos Ramírez" and detalle_trabajador_id == asignaciones[0][0]
                comision = conexion.execute(
                    """INSERT INTO comisiones
                       (detalle_trabajador_id, fecha_generacion, monto, desprendible_id,
                        pagado, fecha_pago)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        detalle_trabajador_id, fecha_comision, monto,
                        desprendible_id if esta_pagada else None,
                        1 if esta_pagada else 0,
                        fecha_comision if esta_pagada else None,
                    ),
                )
                if esta_pagada:
                    conexion.execute(
                        """INSERT INTO detalle_desprendible (desprendible_id, comision_id)
                           VALUES (?, ?)""",
                        (desprendible_id, comision.lastrowid),
                    )

            conexion.executemany(
                """INSERT INTO gastos
                   (fecha, categoria_id, concepto, monto, proveedor_id, estado, fecha_pago, notas)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (hace_tres_dias, categorias_gasto["Insumos"],
                     "Compra de electrodos y discos", 125000,
                     proveedores["Suministros Industriales"], "pagado", hace_dos_dias,
                     "Gasto de prueba pagado."),
                    (hace_un_dia, categorias_gasto["Servicios básicos"],
                     "Servicio de energía", 185000, None, "pendiente", None,
                     "Gasto de prueba pendiente."),
                    (hace_dos_dias, categorias_gasto["Otros"],
                     "Repuestos para mantenimiento", 68000,
                     proveedores["Repuestos La 14"], "pagado", hace_un_dia,
                     "Gasto de prueba pagado."),
                ],
            )

    return destino


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Genera una base separada con datos ficticios para probar PDFs."
    )
    parser.add_argument(
        "--salida", type=Path, default=RUTA_POR_DEFECTO,
        help=f"ruta de salida (predeterminada: {RUTA_POR_DEFECTO.name})",
    )
    parser.add_argument(
        "--sobrescribir", action="store_true",
        help="reemplaza el archivo de salida si ya existe",
    )
    argumentos = parser.parse_args()
    ruta = crear_base_pruebas(argumentos.salida.resolve(), argumentos.sobrescribir)
    print(f"Base de pruebas creada: {ruta}")


if __name__ == "__main__":
    main()
