"""Acceso a datos SQLite para los catálogos del taller."""

from pathlib import Path
from contextlib import closing
import sqlite3
from datetime import date, timedelta
import sys
from typing import Any


_DIRECTORIO_MODULO = Path(__file__).resolve().parent
_DIRECTORIO_RECURSOS = Path(getattr(sys, "_MEIPASS", _DIRECTORIO_MODULO))
_DIRECTORIO_DATOS = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False) else _DIRECTORIO_MODULO
)
RUTA_BD = _DIRECTORIO_DATOS / "taller.db"
RUTA_SCHEMA = _DIRECTORIO_RECURSOS / "schema.sql"


class ErrorBaseDatos(Exception):
    """Error de una operación de persistencia."""


def inicializar_bd() -> None:
    """Crea la base de datos y carga el esquema y los datos iniciales."""
    try:
        if not RUTA_BD.exists():
            # El esquema se ejecuta solo al crear una base nueva; no se alteran
            # bases existentes al arrancar para preservar los datos del taller.
            with closing(sqlite3.connect(RUTA_BD)) as conexion:
                with conexion:
                    conexion.execute("PRAGMA foreign_keys = ON")
                    conexion.executescript(RUTA_SCHEMA.read_text(encoding="utf-8"))
    except (OSError, sqlite3.Error) as error:
        raise ErrorBaseDatos(f"No se pudo inicializar la base de datos: {error}") from error


def _conectar() -> sqlite3.Connection:
    """Abre SQLite con filas nombradas y claves foráneas habilitadas."""
    conexion = sqlite3.connect(RUTA_BD)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def _consultar(sql: str, parametros: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    """Ejecuta una lectura parametrizada y convierte cada fila en diccionario."""
    try:
        with closing(_conectar()) as conexion:
            with conexion:
                return [dict(fila) for fila in conexion.execute(sql, parametros).fetchall()]
    except sqlite3.Error as error:
        raise ErrorBaseDatos(f"No se pudo consultar la base de datos: {error}") from error


def _ejecutar(sql: str, parametros: tuple[Any, ...] = ()) -> int:
    """Ejecuta una escritura aislada y retorna el identificador/resultado."""
    try:
        with closing(_conectar()) as conexion:
            with conexion:
                cursor = conexion.execute(sql, parametros)
                return int(cursor.lastrowid or cursor.rowcount)
    except sqlite3.Error as error:
        raise ErrorBaseDatos(f"No se pudo guardar en la base de datos: {error}") from error


def _eliminar(sql: str, parametros: tuple[Any, ...]) -> None:
    try:
        with closing(_conectar()) as conexion:
            with conexion:
                conexion.execute(sql, parametros)
    except sqlite3.Error as error:
        raise ErrorBaseDatos(f"No se pudo eliminar el registro: {error}") from error


def productos_listar(busqueda: str = "") -> list[dict[str, Any]]:
    """Lista productos activos y permite buscar por nombre."""
    patron = f"%{busqueda.strip()}%"
    return _consultar(
        """SELECT p.id, p.nombre, p.categoria_id, c.nombre AS categoria,
                  p.precio_compra, p.precio_venta, p.stock, p.stock_minimo, p.activo
           FROM productos p LEFT JOIN categorias c ON c.id = p.categoria_id
           WHERE p.activo = 1 AND p.nombre LIKE ? COLLATE NOCASE
           ORDER BY p.nombre""",
        (patron,),
    )


def productos_insertar(nombre: str, categoria_id: int | None, precio_compra: float,
                       precio_venta: float, stock: int, stock_minimo: int) -> int:
    return _ejecutar(
        """INSERT INTO productos
           (nombre, categoria_id, precio_compra, precio_venta, stock, stock_minimo)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (nombre, categoria_id, precio_compra, precio_venta, stock, stock_minimo),
    )


def productos_actualizar(producto_id: int, nombre: str, categoria_id: int | None,
                         precio_compra: float, precio_venta: float, stock: int,
                         stock_minimo: int) -> int:
    return _ejecutar(
        """UPDATE productos SET nombre=?, categoria_id=?, precio_compra=?,
           precio_venta=?, stock=?, stock_minimo=? WHERE id=?""",
        (nombre, categoria_id, precio_compra, precio_venta, stock, stock_minimo, producto_id),
    )


def productos_eliminar(producto_id: int) -> None:
    _eliminar("DELETE FROM productos WHERE id=?", (producto_id,))


def categorias_listar() -> list[dict[str, Any]]:
    """Lista las categorías de producto disponibles."""
    return _consultar("SELECT id, nombre FROM categorias ORDER BY nombre")


def categorias_insertar(nombre: str) -> int:
    return _ejecutar("INSERT INTO categorias (nombre) VALUES (?)", (nombre,))


def categorias_actualizar(categoria_id: int, nombre: str) -> int:
    return _ejecutar("UPDATE categorias SET nombre=? WHERE id=?", (nombre, categoria_id))


def categorias_eliminar(categoria_id: int) -> None:
    _eliminar("DELETE FROM categorias WHERE id=?", (categoria_id,))


def servicios_listar() -> list[dict[str, Any]]:
    """Lista los servicios activos para documentos y formularios."""
    return _consultar(
        """SELECT id, nombre, categoria, descripcion, precio_cliente,
                  porcentaje_default, activo
           FROM servicios WHERE activo=1 ORDER BY nombre"""
    )


def servicios_insertar(nombre: str, categoria: str, descripcion: str,
                       precio_cliente: float, porcentaje_default: float) -> int:
    return _ejecutar(
        """INSERT INTO servicios
           (nombre, categoria, descripcion, precio_cliente, porcentaje_default)
           VALUES (?, ?, ?, ?, ?)""",
        (nombre, categoria, descripcion, precio_cliente, porcentaje_default),
    )


def servicios_actualizar(servicio_id: int, nombre: str, categoria: str, descripcion: str,
                         precio_cliente: float, porcentaje_default: float) -> int:
    return _ejecutar(
        """UPDATE servicios SET nombre=?, categoria=?, descripcion=?,
           precio_cliente=?, porcentaje_default=? WHERE id=?""",
        (nombre, categoria, descripcion, precio_cliente, porcentaje_default, servicio_id),
    )


def servicios_eliminar(servicio_id: int) -> None:
    _eliminar("DELETE FROM servicios WHERE id=?", (servicio_id,))


def trabajadores_listar() -> list[dict[str, Any]]:
    """Lista trabajadores activos para asignaciones y nómina."""
    return _consultar(
        "SELECT id, cedula, nombre, cargo, activo FROM trabajadores WHERE activo=1 ORDER BY nombre"
    )


def trabajadores_insertar(cedula: str, nombre: str, cargo: str) -> int:
    return _ejecutar(
        "INSERT INTO trabajadores (cedula, nombre, cargo) VALUES (?, ?, ?)",
        (cedula, nombre, cargo),
    )


def trabajadores_actualizar(trabajador_id: int, cedula: str, nombre: str, cargo: str) -> int:
    return _ejecutar(
        "UPDATE trabajadores SET cedula=?, nombre=?, cargo=? WHERE id=?",
        (cedula, nombre, cargo, trabajador_id),
    )


def trabajadores_eliminar(trabajador_id: int) -> None:
    _ejecutar("UPDATE trabajadores SET activo=0 WHERE id=?", (trabajador_id,))


def _personas_listar(tabla: str) -> list[dict[str, Any]]:
    if tabla not in {"clientes", "proveedores"}:
        raise ValueError("Entidad no permitida")
    return _consultar(
        f"""SELECT id, nombre, telefono, direccion, email, notas, activo
            FROM {tabla} WHERE activo=1 ORDER BY nombre"""
    )


def _personas_insertar(tabla: str, nombre: str, telefono: str,
                       direccion: str, email: str, notas: str) -> int:
    if tabla not in {"clientes", "proveedores"}:
        raise ValueError("Entidad no permitida")
    return _ejecutar(
        f"INSERT INTO {tabla} (nombre, telefono, direccion, email, notas) VALUES (?, ?, ?, ?, ?)",
        (nombre, telefono, direccion, email, notas),
    )


def _personas_actualizar(tabla: str, persona_id: int, nombre: str, telefono: str,
                         direccion: str, email: str, notas: str) -> int:
    if tabla not in {"clientes", "proveedores"}:
        raise ValueError("Entidad no permitida")
    return _ejecutar(
        f"""UPDATE {tabla} SET nombre=?, telefono=?, direccion=?, email=?, notas=?
            WHERE id=?""",
        (nombre, telefono, direccion, email, notas, persona_id),
    )


def _personas_eliminar(tabla: str, persona_id: int) -> None:
    if tabla not in {"clientes", "proveedores"}:
        raise ValueError("Entidad no permitida")
    _eliminar(f"DELETE FROM {tabla} WHERE id=?", (persona_id,))


def clientes_listar() -> list[dict[str, Any]]:
    """Lista los clientes activos."""
    return _personas_listar("clientes")


def clientes_insertar(nombre: str, telefono: str, direccion: str, email: str, notas: str) -> int:
    return _personas_insertar("clientes", nombre, telefono, direccion, email, notas)


def clientes_actualizar(cliente_id: int, nombre: str, telefono: str,
                        direccion: str, email: str, notas: str) -> int:
    return _personas_actualizar("clientes", cliente_id, nombre, telefono, direccion, email, notas)


def clientes_eliminar(cliente_id: int) -> None:
    _personas_eliminar("clientes", cliente_id)


def proveedores_listar() -> list[dict[str, Any]]:
    """Lista los proveedores activos."""
    return _personas_listar("proveedores")


def proveedores_insertar(nombre: str, telefono: str, direccion: str,
                         email: str, notas: str) -> int:
    return _personas_insertar("proveedores", nombre, telefono, direccion, email, notas)


def proveedores_actualizar(proveedor_id: int, nombre: str, telefono: str,
                           direccion: str, email: str, notas: str) -> int:
    return _personas_actualizar(
        "proveedores", proveedor_id, nombre, telefono, direccion, email, notas
    )


def proveedores_eliminar(proveedor_id: int) -> None:
    _personas_eliminar("proveedores", proveedor_id)


_CAMPOS_DOCUMENTO = {
    "tipo", "numero", "fecha_emision", "cliente_id", "documento_origen_id",
    "fecha_inicio", "fecha_entrega", "equipo", "placa", "serial_ot",
    "tiempo_estimado", "falla_reportada", "causa_falla", "trabajos_ejecutados",
    "recomendaciones", "subtotal", "total", "estado", "notas",
}
_TIPOS_DOCUMENTO = {"factura", "cotizacion", "orden_servicio", "orden_trabajo"}


def siguiente_numero(tipo: str) -> int:
    """Retorna el próximo consecutivo de un tipo de documento."""
    if tipo not in _TIPOS_DOCUMENTO:
        raise ValueError(f"Tipo de documento no válido: {tipo}")
    filas = _consultar(
        "SELECT COALESCE(MAX(numero), 0) + 1 AS siguiente FROM documentos WHERE tipo=?",
        (tipo,),
    )
    return int(filas[0]["siguiente"])


def documentos_listar(filtros: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Lista documentos y aplica únicamente los filtros proporcionados."""
    filtros = filtros or {}
    condiciones: list[str] = []
    parametros: list[Any] = []
    for llave, columna in (
        ("tipo", "d.tipo"), ("cliente_id", "d.cliente_id"), ("estado", "d.estado"),
    ):
        valor = filtros.get(llave)
        if valor not in (None, "", "Todos"):
            condiciones.append(f"{columna} = ?")
            parametros.append(valor)
    fecha_desde = filtros.get("fecha_desde")
    fecha_hasta = filtros.get("fecha_hasta")
    if fecha_desde:
        condiciones.append("d.fecha_emision >= ?")
        parametros.append(fecha_desde)
    if fecha_hasta:
        condiciones.append("d.fecha_emision <= ?")
        parametros.append(fecha_hasta)
    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
    return _consultar(
        f"""SELECT d.*, c.nombre AS cliente
            FROM documentos d LEFT JOIN clientes c ON c.id = d.cliente_id
            {where}
            ORDER BY d.fecha_emision DESC, d.id DESC""",
        tuple(parametros),
    )


def documentos_obtener(documento_id: int) -> dict[str, Any] | None:
    """Carga cabecera, cliente y detalle completo de un documento."""
    filas = _consultar(
        """SELECT d.*, c.nombre AS cliente
           FROM documentos d LEFT JOIN clientes c ON c.id=d.cliente_id
           WHERE d.id=?""",
        (documento_id,),
    )
    if not filas:
        return None
    documento = filas[0]
    documento["detalle"] = detalle_listar(documento_id)
    return documento


def documentos_insertar(**datos: Any) -> int:
    """Inserta una cabecera documental y asigna tipo, número y fecha por defecto."""
    campos = [campo for campo in datos if campo in _CAMPOS_DOCUMENTO]
    tipo = datos.get("tipo")
    if tipo not in _TIPOS_DOCUMENTO:
        raise ValueError("El tipo de documento es obligatorio y debe ser válido.")
    if not datos.get("numero"):
        datos["numero"] = siguiente_numero(tipo)
        if "numero" not in campos:
            campos.append("numero")
    if not datos.get("fecha_emision"):
        datos["fecha_emision"] = date.today().isoformat()
        if "fecha_emision" not in campos:
            campos.append("fecha_emision")
    valores = [datos[campo] for campo in campos]
    placeholders = ", ".join("?" for _ in campos)
    return _ejecutar(
        f"INSERT INTO documentos ({', '.join(campos)}) VALUES ({placeholders})",
        tuple(valores),
    )


def documentos_actualizar(documento_id: int, **datos: Any) -> int:
    """Actualiza solo los campos reconocidos, conservando el consecutivo."""
    campos = [campo for campo in datos if campo in _CAMPOS_DOCUMENTO and campo != "numero"]
    if not campos:
        raise ValueError("No se proporcionaron campos válidos para actualizar.")
    if "tipo" in datos and datos["tipo"] not in _TIPOS_DOCUMENTO:
        raise ValueError("El tipo de documento no es válido.")
    asignaciones = ", ".join(f"{campo}=?" for campo in campos)
    return _ejecutar(
        f"UPDATE documentos SET {asignaciones} WHERE id=?",
        tuple(datos[campo] for campo in campos) + (documento_id,),
    )


def _detalles_listar_tx(conexion: sqlite3.Connection, documento_id: int) -> list[dict[str, Any]]:
    filas = conexion.execute(
        """SELECT dd.*, CASE dd.item_tipo
                    WHEN 'producto' THEN p.nombre ELSE s.nombre END AS descripcion
           FROM detalle_documentos dd
           LEFT JOIN productos p ON dd.item_tipo='producto' AND p.id=dd.item_id
           LEFT JOIN servicios s ON dd.item_tipo='servicio' AND s.id=dd.item_id
           WHERE dd.documento_id=? ORDER BY dd.id""",
        (documento_id,),
    ).fetchall()
    resultado = []
    for fila in filas:
        detalle = dict(fila)
        detalle["trabajadores"] = [
            dict(trabajador) for trabajador in conexion.execute(
                """SELECT dt.id, dt.trabajador_id, t.nombre AS trabajador, dt.porcentaje
                   FROM detalle_trabajadores dt
                   JOIN trabajadores t ON t.id=dt.trabajador_id
                   WHERE dt.detalle_id=? ORDER BY dt.id""",
                (detalle["id"],),
            ).fetchall()
        ]
        resultado.append(detalle)
    return resultado


def detalle_listar(documento_id: int) -> list[dict[str, Any]]:
    """Lista líneas de un documento con nombre y asignaciones de trabajadores."""
    try:
        with closing(_conectar()) as conexion:
            return _detalles_listar_tx(conexion, documento_id)
    except sqlite3.Error as error:
        raise ErrorBaseDatos(f"No se pudo consultar el detalle: {error}") from error


def detalle_insertar(documento_id: int, item_tipo: str, item_id: int,
                     cantidad: float, precio_unitario: float, subtotal: float) -> int:
    if item_tipo not in {"producto", "servicio"}:
        raise ValueError("Tipo de artículo no válido.")
    return _ejecutar(
        """INSERT INTO detalle_documentos
           (documento_id, item_tipo, item_id, cantidad, precio_unitario, subtotal)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (documento_id, item_tipo, item_id, cantidad, precio_unitario, subtotal),
    )


def detalle_trabajadores_listar(detalle_id: int | None = None) -> list[dict[str, Any]]:
    """Lista asignaciones de trabajador para una línea o para todo el catálogo."""
    sql = """SELECT dt.id, dt.detalle_id, dt.trabajador_id, t.nombre AS trabajador,
                    dt.porcentaje
             FROM detalle_trabajadores dt
             JOIN trabajadores t ON t.id=dt.trabajador_id"""
    parametros: tuple[Any, ...] = ()
    if detalle_id is not None:
        sql += " WHERE dt.detalle_id=?"
        parametros = (detalle_id,)
    sql += " ORDER BY dt.id"
    return _consultar(sql, parametros)


def detalle_trabajadores_insertar(detalle_id: int, trabajador_id: int,
                                  porcentaje: float) -> int:
    return _ejecutar(
        """INSERT INTO detalle_trabajadores (detalle_id, trabajador_id, porcentaje)
           VALUES (?, ?, ?)""",
        (detalle_id, trabajador_id, porcentaje),
    )


def comisiones_listar_pendientes(
    trabajador_id: int, desde: str | None = None, hasta: str | None = None
) -> list[dict[str, Any]]:
    """Busca comisiones no liquidadas y opcionalmente limita sus fechas."""
    condiciones = ["dt.trabajador_id=?", "c.pagado=0", "c.desprendible_id IS NULL"]
    parametros: list[Any] = [trabajador_id]
    if desde:
        condiciones.append("c.fecha_generacion >= ?")
        parametros.append(desde)
    if hasta:
        condiciones.append("c.fecha_generacion <= ?")
        parametros.append(hasta)
    where = " AND ".join(condiciones)
    return _consultar(
        f"""SELECT c.id, c.fecha_generacion, c.monto, c.pagado,
                   dt.porcentaje, dt.id AS detalle_trabajador_id,
                   d.id AS documento_id, d.tipo, d.numero,
                   s.nombre AS servicio, t.nombre AS trabajador
           FROM comisiones c
           JOIN detalle_trabajadores dt ON dt.id=c.detalle_trabajador_id
           JOIN detalle_documentos dd ON dd.id=dt.detalle_id
           JOIN documentos d ON d.id=dd.documento_id
           LEFT JOIN servicios s ON dd.item_tipo='servicio' AND s.id=dd.item_id
           JOIN trabajadores t ON t.id=dt.trabajador_id
           WHERE {where}
           ORDER BY c.fecha_generacion, c.id""",
        tuple(parametros),
    )


def comisiones_insertar(detalle_trabajador_id: int, fecha_generacion: str,
                        monto: float, desprendible_id: int | None = None) -> int:
    return _ejecutar(
        """INSERT INTO comisiones
           (detalle_trabajador_id, fecha_generacion, monto, desprendible_id)
           VALUES (?, ?, ?, ?)""",
        (detalle_trabajador_id, fecha_generacion, monto, desprendible_id),
    )


def desprendibles_listar(trabajador_id: int) -> list[dict[str, Any]]:
    """Lista el historial de liquidaciones de un trabajador."""
    return _consultar(
        """SELECT id, numero, trabajador_id, fecha_emision, periodo_inicio,
                  periodo_fin, total, estado
           FROM desprendibles WHERE trabajador_id=?
           ORDER BY fecha_emision DESC, numero DESC""",
        (trabajador_id,),
    )


def desprendibles_insertar(
    trabajador_id: int, fecha_emision: str, periodo_inicio: str | None,
    periodo_fin: str | None, total: float, estado: str = "pagado",
) -> int:
    return _ejecutar(
        """INSERT INTO desprendibles
           (numero, trabajador_id, fecha_emision, periodo_inicio, periodo_fin, total, estado)
           VALUES (
               (SELECT COALESCE(MAX(numero), 0) + 1 FROM desprendibles WHERE trabajador_id=?),
               ?, ?, ?, ?, ?, ?
           )""",
        (trabajador_id, trabajador_id, fecha_emision, periodo_inicio, periodo_fin, total, estado),
    )


def detalle_desprendible_insertar(desprendible_id: int, comision_id: int) -> int:
    return _ejecutar(
        """INSERT INTO detalle_desprendible (desprendible_id, comision_id)
           VALUES (?, ?)""",
        (desprendible_id, comision_id),
    )


def nomina_generar_desprendible(
    trabajador_id: int, desde: str | None = None, hasta: str | None = None,
    incluir_todas: bool = False,
) -> int:
    """Liquida las comisiones elegibles y crea su desprendible atómicamente."""
    try:
        with closing(_conectar()) as conexion:
            with conexion:
                condiciones = [
                    "dt.trabajador_id=?", "c.pagado=0", "c.desprendible_id IS NULL"
                ]
                parametros: list[Any] = [trabajador_id]
                if not incluir_todas:
                    if desde:
                        condiciones.append("c.fecha_generacion >= ?")
                        parametros.append(desde)
                    if hasta:
                        condiciones.append("c.fecha_generacion <= ?")
                        parametros.append(hasta)
                filas = conexion.execute(
                    """SELECT c.id, c.monto FROM comisiones c
                       JOIN detalle_trabajadores dt ON dt.id=c.detalle_trabajador_id
                       WHERE """ + " AND ".join(condiciones) + " ORDER BY c.id",
                    tuple(parametros),
                ).fetchall()
                if not filas:
                    raise ValueError("No hay comisiones pendientes en el período seleccionado.")
                # La misma transacción reserva cada comisión: otro intento no
                # puede volver a incluirla en un segundo desprendible.
                fecha_emision = date.today().isoformat()
                total = sum(float(fila["monto"] or 0) for fila in filas)
                cursor = conexion.execute(
                    """INSERT INTO desprendibles
                       (numero, trabajador_id, fecha_emision, periodo_inicio,
                        periodo_fin, total, estado)
                       VALUES (
                         (SELECT COALESCE(MAX(numero),0)+1 FROM desprendibles
                          WHERE trabajador_id=?),
                         ?, ?, ?, ?, ?, 'pagado'
                       )""",
                    (
                        trabajador_id, trabajador_id, fecha_emision,
                        None if incluir_todas else desde,
                        None if incluir_todas else hasta, total,
                    ),
                )
                desprendible_id = int(cursor.lastrowid)
                for comision in filas:
                    actualizado = conexion.execute(
                        """UPDATE comisiones SET pagado=1, fecha_pago=?, desprendible_id=?
                           WHERE id=? AND pagado=0 AND desprendible_id IS NULL""",
                        (fecha_emision, desprendible_id, comision["id"]),
                    )
                    if actualizado.rowcount != 1:
                        raise ValueError(
                            "Una comisión ya fue liquidada en otra operación. "
                            "Actualice la lista e inténtelo nuevamente."
                        )
                    conexion.execute(
                        """INSERT INTO detalle_desprendible (desprendible_id, comision_id)
                           VALUES (?, ?)""",
                        (desprendible_id, comision["id"]),
                    )
                return desprendible_id
    except sqlite3.Error as error:
        raise ErrorBaseDatos(f"No se pudo generar el desprendible: {error}") from error


def desprendible_obtener(desprendible_id: int) -> dict[str, Any] | None:
    filas = _consultar(
        """SELECT d.*, t.nombre AS trabajador, t.cedula, t.cargo
           FROM desprendibles d JOIN trabajadores t ON t.id=d.trabajador_id
           WHERE d.id=?""",
        (desprendible_id,),
    )
    if not filas:
        return None
    desprendible = filas[0]
    desprendible["comisiones"] = _consultar(
        """SELECT c.id, c.fecha_generacion, c.monto, dt.porcentaje,
                  s.nombre AS servicio
           FROM detalle_desprendible dd
           JOIN comisiones c ON c.id=dd.comision_id
           JOIN detalle_trabajadores dt ON dt.id=c.detalle_trabajador_id
           JOIN detalle_documentos det ON det.id=dt.detalle_id
           LEFT JOIN servicios s ON det.item_tipo='servicio' AND s.id=det.item_id
           WHERE dd.desprendible_id=? ORDER BY c.fecha_generacion, c.id""",
        (desprendible_id,),
    )
    return desprendible


def _validar_lineas(lineas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normaliza líneas y valida tipo, cantidad, precio y porcentajes."""
    resultado: list[dict[str, Any]] = []
    for linea in lineas:
        item_tipo = linea.get("item_tipo", linea.get("tipo"))
        if item_tipo not in {"producto", "servicio"}:
            raise ValueError("Cada línea debe ser un producto o un servicio.")
        item_id = int(linea["item_id"])
        cantidad = float(linea["cantidad"])
        precio = float(linea["precio_unitario"])
        if item_id <= 0 or cantidad <= 0 or precio < 0:
            raise ValueError("Las líneas deben tener artículo y cantidad válida.")
        trabajadores = linea.get("trabajadores", [])
        normalizados = []
        for asignacion in trabajadores:
            trabajador_id = int(asignacion["trabajador_id"])
            porcentaje = float(asignacion["porcentaje"])
            if trabajador_id <= 0 or not 0 <= porcentaje <= 100:
                raise ValueError("Trabajador o porcentaje de comisión no válido.")
            normalizados.append({
                "trabajador_id": trabajador_id,
                "porcentaje": porcentaje,
            })
        resultado.append({
            "item_tipo": item_tipo,
            "item_id": item_id,
            "cantidad": cantidad,
            "precio_unitario": precio,
            "subtotal": cantidad * precio,
            "trabajadores": normalizados,
        })
    if not resultado:
        raise ValueError("Agregue al menos una línea al documento.")
    return resultado


def _impacta_inventario_tx(conexion: sqlite3.Connection, documento: dict[str, Any]) -> bool:
    """Evita descontar dos veces: la factura derivada de una OS no mueve stock."""
    if documento["tipo"] == "orden_servicio":
        return True
    if documento["tipo"] != "factura":
        return False
    origen_id = documento.get("documento_origen_id")
    if origen_id is None:
        return True
    origen = conexion.execute(
        "SELECT tipo FROM documentos WHERE id=?", (origen_id,)
    ).fetchone()
    return not origen or origen["tipo"] != "orden_servicio"


def _ajustar_inventario_tx(
    conexion: sqlite3.Connection, lineas: list[dict[str, Any]], direccion: int
) -> None:
    """Suma o resta existencias; dirección -1 vende y +1 revierte una venta."""
    for linea in lineas:
        if linea["item_tipo"] != "producto":
            continue
        fila = conexion.execute(
            "SELECT nombre, stock FROM productos WHERE id=? AND activo=1",
            (linea["item_id"],),
        ).fetchone()
        if not fila:
            raise ValueError(f"El producto con ID {linea['item_id']} no existe o está inactivo.")
        unidades = linea["cantidad"]
        if not unidades.is_integer():
            raise ValueError(f"La cantidad del producto {fila['nombre']} debe ser entera.")
        nuevo_stock = fila["stock"] + direccion * int(unidades)
        if nuevo_stock < 0:
            raise ValueError(
                f"Stock insuficiente para {fila['nombre']}. Disponible: {fila['stock']}."
            )
        conexion.execute(
            "UPDATE productos SET stock=? WHERE id=?",
            (nuevo_stock, linea["item_id"]),
        )


def _limpiar_detalle_tx(conexion: sqlite3.Connection, documento_id: int) -> None:
    """Elimina relaciones del detalle y protege comisiones ya liquidadas."""
    detalles = conexion.execute(
        "SELECT id FROM detalle_documentos WHERE documento_id=?", (documento_id,)
    ).fetchall()
    for fila in detalles:
        comisiones = conexion.execute(
            """SELECT c.id, c.pagado, c.desprendible_id FROM comisiones c
               JOIN detalle_trabajadores dt ON dt.id=c.detalle_trabajador_id
               WHERE dt.detalle_id=?""",
            (fila["id"],),
        ).fetchall()
        for comision in comisiones:
            if comision["pagado"] or comision["desprendible_id"] is not None:
                raise ValueError(
                    "No se puede modificar: el trabajador ya recibió esta comisión "
                    "o está incluida en un desprendible."
                )
            tiene_desprendible = conexion.execute(
                "SELECT 1 FROM detalle_desprendible WHERE comision_id=?",
                (comision["id"],),
            ).fetchone()
            if tiene_desprendible:
                raise ValueError(
                    "No se puede modificar: una comisión ya está asociada a un desprendible."
                )
            conexion.execute("DELETE FROM comisiones WHERE id=?", (comision["id"],))
        conexion.execute("DELETE FROM detalle_trabajadores WHERE detalle_id=?", (fila["id"],))
    conexion.execute("DELETE FROM detalle_documentos WHERE documento_id=?", (documento_id,))


def _guardar_documento_tx(
    conexion: sqlite3.Connection,
    datos: dict[str, Any],
    lineas: list[dict[str, Any]],
    documento_id: int | None = None,
    generar_comisiones: bool = False,
) -> int:
    """Guarda cabecera, detalle, inventario y comisiones en la transacción actual."""
    tipo = datos.get("tipo")
    if tipo not in _TIPOS_DOCUMENTO:
        raise ValueError("Tipo de documento no válido.")
    lineas = _validar_lineas(lineas)
    if tipo in {"orden_trabajo", "orden_servicio"} and any(
        linea["item_tipo"] == "servicio" and not linea["trabajadores"]
        for linea in lineas
    ):
        nombre_tipo = "orden de trabajo" if tipo == "orden_trabajo" else "orden de servicio"
        raise ValueError(f"Asigne al menos un trabajador a cada servicio de la {nombre_tipo}.")
    total = sum(linea["subtotal"] for linea in lineas)
    valores = {campo: datos.get(campo) for campo in _CAMPOS_DOCUMENTO}
    valores.update({
        "tipo": tipo,
        "fecha_emision": datos.get("fecha_emision") or date.today().isoformat(),
        "subtotal": total,
        "total": total,
        "estado": datos.get("estado") or "emitida",
    })
    if valores.get("cliente_id") is None:
        raise ValueError("Seleccione un cliente para el documento.")

    anterior = None
    lineas_anteriores: list[dict[str, Any]] = []
    if documento_id is not None:
        fila = conexion.execute("SELECT * FROM documentos WHERE id=?", (documento_id,)).fetchone()
        if not fila:
            raise ValueError("El documento que intenta editar ya no existe.")
        anterior = dict(fila)
        if anterior["tipo"] == "cotizacion" and anterior["estado"] == "aprobada":
            raise ValueError("No se puede editar una cotización que ya fue aprobada.")
        lineas_anteriores = _detalles_listar_tx(conexion, documento_id)
        # Al editar primero se devuelve al inventario el detalle anterior;
        # luego se valida y aplica el nuevo detalle antes de confirmar.
        if _impacta_inventario_tx(conexion, anterior):
            _ajustar_inventario_tx(conexion, lineas_anteriores, 1)
        _limpiar_detalle_tx(conexion, documento_id)
        valores["numero"] = anterior["numero"]
        valores["documento_origen_id"] = (
            datos.get("documento_origen_id", anterior["documento_origen_id"])
        )
        asignaciones = ", ".join(f"{campo}=?" for campo in valores)
        conexion.execute(
            f"UPDATE documentos SET {asignaciones} WHERE id=?",
            tuple(valores.values()) + (documento_id,),
        )
        nuevo_id = documento_id
    else:
        valores["numero"] = _siguiente_numero_tx(conexion, tipo)
        columnas = list(valores)
        cursores = conexion.execute(
            f"INSERT INTO documentos ({', '.join(columnas)}) "
            f"VALUES ({', '.join('?' for _ in columnas)})",
            tuple(valores[campo] for campo in columnas),
        )
        nuevo_id = int(cursores.lastrowid)

    if _impacta_inventario_tx(conexion, valores):
        _ajustar_inventario_tx(conexion, lineas, -1)

    for linea in lineas:
        cursor = conexion.execute(
            """INSERT INTO detalle_documentos
               (documento_id, item_tipo, item_id, cantidad, precio_unitario, subtotal)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (nuevo_id, linea["item_tipo"], linea["item_id"], linea["cantidad"],
             linea["precio_unitario"], linea["subtotal"]),
        )
        detalle_id = int(cursor.lastrowid)
        for asignacion in linea["trabajadores"]:
            cursor_trabajador = conexion.execute(
                """INSERT INTO detalle_trabajadores (detalle_id, trabajador_id, porcentaje)
                   VALUES (?, ?, ?)""",
                (detalle_id, asignacion["trabajador_id"], asignacion["porcentaje"]),
            )
            if generar_comisiones and linea["item_tipo"] == "servicio":
                conexion.execute(
                    """INSERT INTO comisiones
                       (detalle_trabajador_id, fecha_generacion, monto)
                       VALUES (?, ?, ?)""",
                    (cursor_trabajador.lastrowid, valores["fecha_emision"],
                     linea["subtotal"] * asignacion["porcentaje"] / 100),
                )
    return nuevo_id


def _siguiente_numero_tx(conexion: sqlite3.Connection, tipo: str) -> int:
    fila = conexion.execute(
        "SELECT COALESCE(MAX(numero), 0) + 1 FROM documentos WHERE tipo=?", (tipo,)
    ).fetchone()
    return int(fila[0])


def documentos_derivado_existe(tipo: str, documento_origen_id: int) -> bool:
    """Indica si ya existe un documento del tipo solicitado para ese origen."""
    filas = _consultar(
        """SELECT 1 FROM documentos
           WHERE tipo=? AND documento_origen_id=? LIMIT 1""",
        (tipo, documento_origen_id),
    )
    return bool(filas)


def _factura_desde_orden_servicio_tx(
    conexion: sqlite3.Connection, orden_servicio_id: int, crear_si_falta: bool
) -> int | None:
    orden = conexion.execute(
        "SELECT * FROM documentos WHERE id=? AND tipo='orden_servicio'",
        (orden_servicio_id,),
    ).fetchone()
    if not orden:
        raise ValueError("La orden de servicio seleccionada no existe.")
    factura = conexion.execute(
        """SELECT id, estado FROM documentos
           WHERE tipo='factura' AND documento_origen_id=? LIMIT 1""",
        (orden_servicio_id,),
    ).fetchone()
    if factura is None and not crear_si_falta:
        return None
    factura_datos = {
        **dict(orden),
        "tipo": "factura",
        "documento_origen_id": orden_servicio_id,
        "estado": "emitida",
    }
    if factura and factura["estado"] == "pagada":
        factura_datos["estado"] = "pagada"
    lineas = [
        {**linea, "trabajadores": []}
        for linea in _detalles_listar_tx(conexion, orden_servicio_id)
    ]
    return _guardar_documento_tx(
        conexion, factura_datos, lineas, int(factura["id"]) if factura else None
    )


def documentos_guardar_flujo(
    datos: dict[str, Any],
    lineas: list[dict[str, Any]],
    documento_id: int | None = None,
    trabajador_ot: int | None = None,
) -> int:
    """Guarda el documento y solo los derivados automáticos de su flujo."""
    try:
        with closing(_conectar()) as conexion:
            with conexion:
                tipo = datos.get("tipo")
                if (
                    tipo == "orden_servicio"
                    and documento_id is None
                    and datos.get("documento_origen_id") is not None
                ):
                    origen = conexion.execute(
                        "SELECT tipo FROM documentos WHERE id=?",
                        (datos["documento_origen_id"],),
                    ).fetchone()
                    if not origen or origen["tipo"] != "orden_trabajo":
                        raise ValueError("La orden de servicio debe estar asociada a una OT válida.")
                    existente = conexion.execute(
                        """SELECT 1 FROM documentos
                           WHERE tipo='orden_servicio' AND documento_origen_id=? LIMIT 1""",
                        (datos["documento_origen_id"],),
                    ).fetchone()
                    if existente:
                        raise ValueError("Esta OT ya tiene una orden de servicio.")
                if tipo == "orden_trabajo":
                    if trabajador_ot:
                        lineas = [
                            {
                                **linea,
                                "trabajadores": (
                                    linea.get("trabajadores")
                                    or [{"trabajador_id": trabajador_ot, "porcentaje": 0}]
                                ) if linea.get("item_tipo", linea.get("tipo")) == "servicio"
                                else linea.get("trabajadores", []),
                            }
                            for linea in lineas
                        ]
                    trabajo_id = _guardar_documento_tx(
                        conexion, datos, lineas, documento_id
                    )
                    if documento_id is not None:
                        os_existente = conexion.execute(
                            """SELECT * FROM documentos
                               WHERE tipo='orden_servicio' AND documento_origen_id=?
                               LIMIT 1""",
                            (trabajo_id,),
                        ).fetchone()
                        if os_existente:
                            trabajo = dict(conexion.execute(
                                "SELECT * FROM documentos WHERE id=?", (trabajo_id,)
                            ).fetchone())
                            datos_os = {
                                **trabajo,
                                "tipo": "orden_servicio",
                                "documento_origen_id": trabajo_id,
                                "causa_falla": os_existente["causa_falla"],
                                "trabajos_ejecutados": os_existente["trabajos_ejecutados"],
                                "recomendaciones": os_existente["recomendaciones"],
                            }
                            os_id = _guardar_documento_tx(
                                conexion,
                                datos_os,
                                _detalles_listar_tx(conexion, trabajo_id),
                                int(os_existente["id"]),
                                generar_comisiones=True,
                            )
                            if conexion.execute(
                                """SELECT 1 FROM documentos
                                   WHERE tipo='factura' AND documento_origen_id=? LIMIT 1""",
                                (os_id,),
                            ).fetchone():
                                _factura_desde_orden_servicio_tx(
                                    conexion, os_id, crear_si_falta=False
                                )
                    return trabajo_id

                documento_nuevo_id = _guardar_documento_tx(
                    conexion, datos, lineas, documento_id,
                    generar_comisiones=(tipo == "orden_servicio"),
                )
                if tipo == "orden_servicio":
                    os_guardada = dict(conexion.execute(
                        "SELECT * FROM documentos WHERE id=?", (documento_nuevo_id,)
                    ).fetchone())
                    origen_id = os_guardada["documento_origen_id"]
                    origen = conexion.execute(
                        "SELECT tipo FROM documentos WHERE id=?", (origen_id,)
                    ).fetchone() if origen_id is not None else None
                    es_os_de_ot = origen is not None and origen["tipo"] == "orden_trabajo"
                    factura_existente = conexion.execute(
                        """SELECT id FROM documentos
                           WHERE tipo='factura' AND documento_origen_id=? LIMIT 1""",
                        (documento_nuevo_id,),
                    ).fetchone()
                    if not es_os_de_ot or factura_existente:
                        _factura_desde_orden_servicio_tx(
                            conexion, documento_nuevo_id, crear_si_falta=not es_os_de_ot
                        )
                return documento_nuevo_id
    except (sqlite3.Error, OSError) as error:
        raise ErrorBaseDatos(f"No se pudo guardar el documento: {error}") from error


def documentos_factura_generar_desde_os(orden_servicio_id: int) -> int:
    """Crea una sola factura asociada a la orden de servicio indicada."""
    try:
        with closing(_conectar()) as conexion:
            with conexion:
                factura_existente = conexion.execute(
                    """SELECT id FROM documentos
                       WHERE tipo='factura' AND documento_origen_id=? LIMIT 1""",
                    (orden_servicio_id,),
                ).fetchone()
                if factura_existente:
                    raise ValueError("Esta orden de servicio ya tiene una factura.")
                factura_id = _factura_desde_orden_servicio_tx(
                    conexion, orden_servicio_id, crear_si_falta=True
                )
                if factura_id is None:
                    raise ValueError("No se pudo generar la factura.")
                return factura_id
    except (sqlite3.Error, OSError) as error:
        raise ErrorBaseDatos(
            f"No se pudo generar la factura desde la orden de servicio: {error}"
        ) from error


def documentos_aprobar_cotizacion(
    cotizacion_id: int, trabajador_id: int | None = None
) -> int:
    """Convierte una cotización con servicios en OT y las demás en factura."""
    try:
        with closing(_conectar()) as conexion:
            with conexion:
                cotizacion = conexion.execute(
                    "SELECT * FROM documentos WHERE id=? AND tipo='cotizacion'",
                    (cotizacion_id,),
                ).fetchone()
                if not cotizacion:
                    raise ValueError("La cotización seleccionada no existe.")
                if cotizacion["estado"] == "aprobada":
                    raise ValueError("Esta cotización ya fue aprobada.")
                datos = dict(cotizacion)
                lineas = _detalles_listar_tx(conexion, cotizacion_id)
                tiene_servicios = any(linea["item_tipo"] == "servicio" for linea in lineas)
                if tiene_servicios:
                    if trabajador_id is None:
                        raise ValueError("Seleccione el trabajador para la orden de trabajo.")
                    for linea in lineas:
                        if linea["item_tipo"] == "servicio":
                            servicio = conexion.execute(
                                "SELECT porcentaje_default FROM servicios WHERE id=?",
                                (linea["item_id"],),
                            ).fetchone()
                            linea["trabajadores"] = [{
                                "trabajador_id": trabajador_id,
                                "porcentaje": (
                                    float(servicio["porcentaje_default"]) if servicio else 0
                                ),
                            }]
                    datos.update({"tipo": "orden_trabajo", "documento_origen_id": cotizacion_id})
                    nuevo_id = _guardar_documento_tx(conexion, datos, lineas)
                    conexion.execute(
                        "UPDATE documentos SET estado='aprobada' WHERE id=?",
                        (cotizacion_id,),
                    )
                    return nuevo_id
                factura_id = _guardar_documento_tx(
                    conexion,
                    {**datos, "tipo": "factura",
                     "documento_origen_id": cotizacion_id, "estado": "emitida"},
                    lineas,
                )
                conexion.execute(
                    "UPDATE documentos SET estado='aprobada' WHERE id=?",
                    (cotizacion_id,),
                )
                return factura_id
    except (sqlite3.Error, OSError) as error:
        raise ErrorBaseDatos(f"No se pudo aprobar la cotización: {error}") from error


def documentos_marcar_pagada(documento_id: int) -> None:
    try:
        with closing(_conectar()) as conexion:
            with conexion:
                cursor = conexion.execute(
                    """UPDATE documentos SET estado='pagada'
                       WHERE id=? AND tipo='factura' AND estado='emitida'""",
                    (documento_id,),
                )
                if cursor.rowcount != 1:
                    raise ValueError("Solo se pueden marcar como pagadas las facturas emitidas.")
    except sqlite3.Error as error:
        raise ErrorBaseDatos(f"No se pudo actualizar el estado de la factura: {error}") from error


def _eliminar_documento_tx(conexion: sqlite3.Connection, documento_id: int) -> None:
    documento = conexion.execute(
        "SELECT * FROM documentos WHERE id=?", (documento_id,)
    ).fetchone()
    if not documento:
        raise ValueError("El documento ya no existe.")
    hijos = conexion.execute(
        "SELECT id FROM documentos WHERE documento_origen_id=?", (documento_id,)
    ).fetchall()
    for hijo in hijos:
        _eliminar_documento_tx(conexion, int(hijo["id"]))
    detalle = _detalles_listar_tx(conexion, documento_id)
    if _impacta_inventario_tx(conexion, dict(documento)):
        _ajustar_inventario_tx(conexion, detalle, 1)
    _limpiar_detalle_tx(conexion, documento_id)
    conexion.execute("DELETE FROM documentos WHERE id=?", (documento_id,))


def documentos_eliminar(documento_id: int) -> None:
    """Elimina los documentos derivados y revierte el inventario afectado."""
    try:
        with closing(_conectar()) as conexion:
            with conexion:
                _eliminar_documento_tx(conexion, documento_id)
    except (sqlite3.Error, OSError) as error:
        raise ErrorBaseDatos(f"No se pudo eliminar el documento: {error}") from error


def categorias_gasto_listar() -> list[dict[str, Any]]:
    """Lista categorías para filtros y formularios de gastos."""
    return _consultar("SELECT id, nombre FROM categorias_gasto ORDER BY nombre")


def categorias_gasto_insertar(nombre: str) -> int:
    return _ejecutar("INSERT INTO categorias_gasto (nombre) VALUES (?)", (nombre.strip(),))


def categorias_gasto_actualizar(categoria_id: int, nombre: str) -> int:
    return _ejecutar(
        "UPDATE categorias_gasto SET nombre=? WHERE id=?", (nombre.strip(), categoria_id)
    )


def categorias_gasto_eliminar(categoria_id: int) -> None:
    try:
        with closing(_conectar()) as conexion:
            with conexion:
                gastos = conexion.execute(
                    "SELECT 1 FROM gastos WHERE categoria_id=? LIMIT 1", (categoria_id,)
                ).fetchone()
                if gastos:
                    raise ValueError("No se puede eliminar la categoría porque tiene gastos.")
                cursor = conexion.execute(
                    "DELETE FROM categorias_gasto WHERE id=?", (categoria_id,)
                )
                if cursor.rowcount != 1:
                    raise ValueError("La categoría seleccionada no existe.")
    except sqlite3.Error as error:
        raise ErrorBaseDatos(f"No se pudo eliminar la categoría de gasto: {error}") from error


def gastos_listar(filtros: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Lista gastos con sus nombres de categoría/proveedor y filtros opcionales."""
    filtros = filtros or {}
    condiciones: list[str] = []
    parametros: list[Any] = []
    for clave, columna in (
        ("categoria_id", "g.categoria_id"), ("estado", "g.estado"),
    ):
        valor = filtros.get(clave)
        if valor not in (None, "", "Todos"):
            condiciones.append(f"{columna}=?")
            parametros.append(valor)
    if filtros.get("fecha_desde"):
        condiciones.append("g.fecha>=?")
        parametros.append(filtros["fecha_desde"])
    if filtros.get("fecha_hasta"):
        condiciones.append("g.fecha<=?")
        parametros.append(filtros["fecha_hasta"])
    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
    return _consultar(
        f"""SELECT g.*, cg.nombre AS categoria, p.nombre AS proveedor
            FROM gastos g
            LEFT JOIN categorias_gasto cg ON cg.id=g.categoria_id
            LEFT JOIN proveedores p ON p.id=g.proveedor_id
            {where}
            ORDER BY g.fecha DESC, g.id DESC""",
        tuple(parametros),
    )


def gastos_insertar(
    fecha: str, categoria_id: int, concepto: str, monto: float,
    proveedor_id: int | None = None, estado: str = "pagado",
    fecha_pago: str | None = None, notas: str = "",
) -> int:
    """Inserta un gasto y normaliza su fecha de pago según su estado."""
    if estado not in {"pagado", "pendiente"}:
        raise ValueError("Estado de gasto no válido.")
    if estado == "pagado" and not fecha_pago:
        fecha_pago = fecha
    if estado == "pendiente":
        fecha_pago = None
    return _ejecutar(
        """INSERT INTO gastos
           (fecha, categoria_id, concepto, monto, proveedor_id, estado, fecha_pago, notas)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (fecha, categoria_id, concepto.strip(), monto, proveedor_id, estado, fecha_pago, notas),
    )


def gastos_actualizar(
    gasto_id: int, fecha: str, categoria_id: int, concepto: str, monto: float,
    proveedor_id: int | None = None, estado: str = "pagado",
    fecha_pago: str | None = None, notas: str = "",
) -> int:
    """Actualiza un gasto manteniendo coherentes estado y fecha de pago."""
    if estado not in {"pagado", "pendiente"}:
        raise ValueError("Estado de gasto no válido.")
    if estado == "pagado" and not fecha_pago:
        fecha_pago = fecha
    if estado == "pendiente":
        fecha_pago = None
    return _ejecutar(
        """UPDATE gastos SET fecha=?, categoria_id=?, concepto=?, monto=?,
           proveedor_id=?, estado=?, fecha_pago=?, notas=? WHERE id=?""",
        (fecha, categoria_id, concepto.strip(), monto, proveedor_id, estado,
         fecha_pago, notas, gasto_id),
    )


def gastos_eliminar(gasto_id: int) -> None:
    _eliminar("DELETE FROM gastos WHERE id=?", (gasto_id,))


def gastos_marcar_pagado(gasto_id: int) -> None:
    try:
        with closing(_conectar()) as conexion:
            with conexion:
                cursor = conexion.execute(
                    """UPDATE gastos SET estado='pagado', fecha_pago=?
                       WHERE id=? AND estado='pendiente'""",
                    (date.today().isoformat(), gasto_id),
                )
                if cursor.rowcount != 1:
                    raise ValueError("El gasto no existe o ya está pagado.")
    except sqlite3.Error as error:
        raise ErrorBaseDatos(f"No se pudo marcar el gasto como pagado: {error}") from error


def _rango_mes(anio: int, mes: int) -> tuple[str, str]:
    """Devuelve el primer y último día ISO del mes indicado."""
    if not 1 <= int(mes) <= 12:
        raise ValueError("El mes debe estar entre 1 y 12.")
    desde = date(int(anio), int(mes), 1)
    siguiente_mes = date(
        int(anio) + (1 if int(mes) == 12 else 0),
        1 if int(mes) == 12 else int(mes) + 1,
        1,
    )
    return desde.isoformat(), (siguiente_mes - timedelta(days=1)).isoformat()


def facturas_pagadas_en_mes(anio: int, mes: int) -> list[dict[str, Any]]:
    """Lista facturas pagadas cuya fecha de emisión cae en el mes."""
    desde, hasta = _rango_mes(anio, mes)
    return _consultar(
        """SELECT d.id, d.numero, d.fecha_emision, d.total, c.nombre AS cliente
           FROM documentos d LEFT JOIN clientes c ON c.id=d.cliente_id
           WHERE d.tipo='factura' AND d.estado='pagada'
             AND d.fecha_emision BETWEEN ? AND ?
           ORDER BY d.fecha_emision, d.numero""",
        (desde, hasta),
    )


def gastos_pagados_en_mes(anio: int, mes: int) -> list[dict[str, Any]]:
    """Lista gastos pagados cuya fecha efectiva de pago cae en el mes."""
    desde, hasta = _rango_mes(anio, mes)
    return _consultar(
        """SELECT g.id, g.fecha_pago, g.concepto, g.monto, cg.nombre AS categoria,
                  p.nombre AS proveedor
           FROM gastos g
           LEFT JOIN categorias_gasto cg ON cg.id=g.categoria_id
           LEFT JOIN proveedores p ON p.id=g.proveedor_id
           WHERE g.estado='pagado' AND g.fecha_pago BETWEEN ? AND ?
           ORDER BY g.fecha_pago, g.id""",
        (desde, hasta),
    )


def desprendibles_en_mes(anio: int, mes: int) -> list[dict[str, Any]]:
    """Lista desprendibles emitidos durante el mes."""
    desde, hasta = _rango_mes(anio, mes)
    return _consultar(
        """SELECT d.id, d.numero, d.fecha_emision, d.total, t.nombre AS trabajador
           FROM desprendibles d JOIN trabajadores t ON t.id=d.trabajador_id
           WHERE d.fecha_emision BETWEEN ? AND ?
           ORDER BY d.fecha_emision, d.id""",
        (desde, hasta),
    )


def facturas_pendientes() -> list[dict[str, Any]]:
    """Lista facturas emitidas y calcula sus días de mora desde la fecha ISO."""
    return _consultar(
        """SELECT d.id, d.numero, d.fecha_emision, d.total, c.nombre AS cliente,
                  CAST(julianday('now') - julianday(d.fecha_emision) AS INTEGER) AS dias_mora
           FROM documentos d LEFT JOIN clientes c ON c.id=d.cliente_id
           WHERE d.tipo='factura' AND d.estado='emitida'
           ORDER BY d.fecha_emision, d.numero"""
    )


def gastos_pendientes() -> list[dict[str, Any]]:
    """Lista gastos pendientes junto con categoría y proveedor."""
    return _consultar(
        """SELECT g.id, g.fecha, g.concepto, g.monto, cg.nombre AS categoria,
                  p.nombre AS proveedor
           FROM gastos g
           LEFT JOIN categorias_gasto cg ON cg.id=g.categoria_id
           LEFT JOIN proveedores p ON p.id=g.proveedor_id
           WHERE g.estado='pendiente'
           ORDER BY g.fecha, g.id"""
    )


def resumen_corte_mensual(anio: int, mes: int) -> dict[str, Any]:
    """Calcula ventas pagadas, nómina, gastos, utilidad y balance del mes."""
    desde, hasta = _rango_mes(anio, mes)
    filas = _consultar(
        """SELECT
             COALESCE(SUM(CASE WHEN dd.item_tipo='producto' THEN dd.subtotal ELSE 0 END),0)
                 AS productos,
             COALESCE(SUM(CASE WHEN dd.item_tipo='servicio' THEN dd.subtotal ELSE 0 END),0)
                 AS servicios
           FROM documentos d
           JOIN detalle_documentos dd ON dd.documento_id=d.id
           WHERE d.tipo='factura' AND d.estado='pagada'
             AND d.fecha_emision BETWEEN ? AND ?""",
        (desde, hasta),
    )
    nomina = _consultar(
        """SELECT COALESCE(SUM(total),0) AS total FROM desprendibles
           WHERE fecha_emision BETWEEN ? AND ?""",
        (desde, hasta),
    )[0]["total"]
    entradas = facturas_pagadas_en_mes(anio, mes)
    gastos = gastos_pagados_en_mes(anio, mes)
    desprendibles = desprendibles_en_mes(anio, mes)
    total_entradas = sum(float(fila["total"] or 0) for fila in entradas)
    total_salidas = sum(float(fila["monto"] or 0) for fila in gastos)
    total_salidas += sum(float(fila["total"] or 0) for fila in desprendibles)
    productos = float(filas[0]["productos"] or 0)
    servicios = float(filas[0]["servicios"] or 0)
    return {
        "productos": productos,
        "servicios": servicios,
        "nomina": float(nomina or 0),
        "utilidad_bruta": productos + servicios - float(nomina or 0),
        "entradas": total_entradas,
        "salidas": total_salidas,
        "balance": total_entradas - total_salidas,
    }


def resumen_dashboard() -> dict[str, Any]:
    """Reúne los indicadores necesarios para las tarjetas de Inicio."""
    hoy = date.today().isoformat()
    inicio_mes, _ = _rango_mes(date.today().year, date.today().month)
    total_stock_bajo = _consultar(
        """SELECT COUNT(*) AS total FROM productos
           WHERE activo=1 AND stock<=stock_minimo"""
    )[0]["total"]
    stock_bajo = _consultar(
        """SELECT p.id, p.nombre, p.stock, p.stock_minimo
           FROM productos p WHERE p.activo=1 AND p.stock<=p.stock_minimo
           ORDER BY p.stock, p.nombre LIMIT 5"""
    )
    venta_hoy = _consultar(
        """SELECT COALESCE(SUM(total),0) AS total FROM documentos
           WHERE tipo='factura' AND estado!='anulada' AND fecha_emision=?""",
        (hoy,),
    )[0]["total"]
    pendiente = _consultar(
        """SELECT COALESCE(SUM(monto),0) AS total FROM comisiones
           WHERE pagado=0 AND desprendible_id IS NULL"""
    )[0]["total"]
    mes = _consultar(
        """SELECT COALESCE(SUM(total),0) AS total FROM documentos
           WHERE tipo='factura' AND estado!='anulada' AND fecha_emision BETWEEN ? AND ?""",
        (inicio_mes, hoy),
    )[0]["total"]
    return {
        "stock_bajo": stock_bajo,
        "total_stock_bajo": int(total_stock_bajo),
        "ventas_hoy": float(venta_hoy or 0),
        "comisiones_pendientes": float(pendiente or 0),
        "facturado_mes": float(mes or 0),
    }
