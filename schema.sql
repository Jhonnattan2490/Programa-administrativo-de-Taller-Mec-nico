PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS categorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    categoria_id INTEGER,
    precio_compra REAL NOT NULL DEFAULT 0,
    precio_venta REAL NOT NULL DEFAULT 0,
    stock INTEGER NOT NULL DEFAULT 0,
    stock_minimo INTEGER NOT NULL DEFAULT 0,
    activo INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (categoria_id) REFERENCES categorias(id)
);

CREATE TABLE IF NOT EXISTS servicios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    categoria TEXT,
    descripcion TEXT,
    precio_cliente REAL NOT NULL DEFAULT 0,
    porcentaje_default REAL NOT NULL DEFAULT 0,
    activo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS trabajadores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cedula TEXT NOT NULL UNIQUE,
    nombre TEXT NOT NULL,
    cargo TEXT NOT NULL,
    activo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    telefono TEXT,
    direccion TEXT,
    email TEXT,
    notas TEXT,
    activo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS proveedores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    telefono TEXT,
    direccion TEXT,
    email TEXT,
    notas TEXT,
    activo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS categorias_gasto (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS documentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT,
    numero INTEGER,
    fecha_emision TEXT,
    cliente_id INTEGER,
    documento_origen_id INTEGER,
    fecha_inicio TEXT,
    fecha_entrega TEXT,
    equipo TEXT,
    placa TEXT,
    serial_ot TEXT,
    tiempo_estimado TEXT,
    falla_reportada TEXT,
    causa_falla TEXT,
    trabajos_ejecutados TEXT,
    recomendaciones TEXT,
    subtotal REAL,
    total REAL,
    estado TEXT DEFAULT 'emitida',
    notas TEXT,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id),
    FOREIGN KEY (documento_origen_id) REFERENCES documentos(id)
);

CREATE TABLE IF NOT EXISTS detalle_documentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    documento_id INTEGER NOT NULL,
    item_tipo TEXT,
    item_id INTEGER,
    cantidad REAL,
    precio_unitario REAL,
    subtotal REAL,
    FOREIGN KEY (documento_id) REFERENCES documentos(id)
);

CREATE TABLE IF NOT EXISTS detalle_trabajadores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    detalle_id INTEGER NOT NULL,
    trabajador_id INTEGER NOT NULL,
    porcentaje REAL,
    FOREIGN KEY (detalle_id) REFERENCES detalle_documentos(id),
    FOREIGN KEY (trabajador_id) REFERENCES trabajadores(id)
);

CREATE TABLE IF NOT EXISTS comisiones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    detalle_trabajador_id INTEGER NOT NULL,
    fecha_generacion TEXT,
    monto REAL,
    desprendible_id INTEGER,
    pagado INTEGER DEFAULT 0,
    fecha_pago TEXT,
    FOREIGN KEY (detalle_trabajador_id) REFERENCES detalle_trabajadores(id),
    FOREIGN KEY (desprendible_id) REFERENCES desprendibles(id)
);

CREATE TABLE IF NOT EXISTS desprendibles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero INTEGER,
    trabajador_id INTEGER NOT NULL,
    fecha_emision TEXT,
    periodo_inicio TEXT,
    periodo_fin TEXT,
    total REAL,
    estado TEXT,
    FOREIGN KEY (trabajador_id) REFERENCES trabajadores(id)
);

CREATE TABLE IF NOT EXISTS detalle_desprendible (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    desprendible_id INTEGER NOT NULL,
    comision_id INTEGER NOT NULL,
    FOREIGN KEY (desprendible_id) REFERENCES desprendibles(id),
    FOREIGN KEY (comision_id) REFERENCES comisiones(id)
);

CREATE TABLE IF NOT EXISTS gastos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT,
    categoria_id INTEGER,
    concepto TEXT,
    monto REAL,
    proveedor_id INTEGER,
    estado TEXT DEFAULT 'pagado',
    fecha_pago TEXT,
    notas TEXT,
    FOREIGN KEY (categoria_id) REFERENCES categorias_gasto(id),
    FOREIGN KEY (proveedor_id) REFERENCES proveedores(id)
);

INSERT OR IGNORE INTO categorias (nombre) VALUES
    ('Soldadura'), ('Mecánica'), ('Repuestos'), ('Herramientas'), ('Insumos');

INSERT OR IGNORE INTO categorias_gasto (nombre) VALUES
    ('Arriendo'), ('Servicios básicos'), ('Insumos'), ('Nómina'), ('Otros');

INSERT INTO servicios (nombre, categoria, descripcion, precio_cliente, porcentaje_default, activo)
SELECT 'Despinchada', 'Mecánica', '', 20000, 40, 1
WHERE NOT EXISTS (SELECT 1 FROM servicios WHERE nombre = 'Despinchada');
INSERT INTO servicios (nombre, categoria, descripcion, precio_cliente, porcentaje_default, activo)
SELECT 'Soldadura', 'Soldadura', '', 50000, 40, 1
WHERE NOT EXISTS (SELECT 1 FROM servicios WHERE nombre = 'Soldadura');
INSERT INTO servicios (nombre, categoria, descripcion, precio_cliente, porcentaje_default, activo)
SELECT 'Mecánica general', 'Mecánica', '', 40000, 35, 1
WHERE NOT EXISTS (SELECT 1 FROM servicios WHERE nombre = 'Mecánica general');
INSERT INTO servicios (nombre, categoria, descripcion, precio_cliente, porcentaje_default, activo)
SELECT 'Engrase', 'Mecánica', '', 15000, 30, 1
WHERE NOT EXISTS (SELECT 1 FROM servicios WHERE nombre = 'Engrase');

INSERT OR IGNORE INTO trabajadores (cedula, nombre, cargo, activo) VALUES
    ('00000001', 'Trabajador de ejemplo 1', 'Mecánico', 1),
    ('00000002', 'Trabajador de ejemplo 2', 'Soldador', 1);
