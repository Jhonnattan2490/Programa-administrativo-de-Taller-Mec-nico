# Sistema de gestión del taller

Aplicación de escritorio offline para la administración de un taller de
mecánica y soldadura. Está hecha con Python, Tkinter/ttk y SQLite; ReportLab
genera los documentos PDF. Está pensada para un solo equipo Windows y un solo
usuario.

## Funcionalidades

- **Inicio:** resumen de productos con stock bajo, ventas del día, comisiones
  pendientes y facturación del mes, con accesos rápidos.
- **Inventario:** productos, categorías, búsqueda y alerta de stock mínimo.
- **Servicios:** catálogo de servicios y porcentajes de comisión sugeridos.
- **Trabajadores:** datos de trabajadores y desactivación lógica.
- **Clientes y proveedores:** catálogos de contactos.
- **Documentos:** facturas, cotizaciones, órdenes de trabajo y órdenes de
  servicio; asignación de trabajadores, inventario, comisiones y PDF.
- **Nómina:** consulta y liquidación de comisiones en desprendibles PDF.
- **Gastos:** registro y seguimiento de gastos pagados y pendientes.
- **Historial:** entradas, salidas, cortes mensuales y pendientes de pago.
- **Interfaz:** pestañas elevadas con bordes y botones azules con estados visuales.

## Requisitos

- Python 3.10 o posterior.
- Tkinter/ttk, incluido en la instalación oficial de Python para Windows.
- ReportLab, instalado desde `requirements.txt`.

## Instalación y ejecución en Windows

Abre una terminal en la carpeta del proyecto y ejecuta:

```bat
py -m pip install -r requirements.txt
py main.py
```

En el primer inicio, la aplicación crea `taller.db` junto a `main.py` y carga
el esquema y los datos iniciales definidos en `schema.sql`.

Los PDFs se guardan en `pdfs/`; la carpeta se crea automáticamente al emitir
el primer documento.

## Estructura

```text
taller_app/
├── main.py                 # Ventana, pestañas y arranque
├── database.py             # SQLite, consultas, CRUD y reglas transaccionales
├── schema.sql              # Tablas y datos semilla
├── requirements.txt        # Dependencias Python
├── README.md
├── pdf/
│   └── generador_pdf.py    # Facturas, cotizaciones y órdenes/desprendibles
├── ui/
│   ├── estilos.py
│   ├── inicio.py
│   ├── inventario.py
│   ├── servicios.py
│   ├── trabajadores.py
│   ├── clientes.py
│   ├── proveedores.py
│   ├── documentos.py
│   ├── nomina.py
│   ├── gastos.py
│   └── historial.py
└── utils/
    ├── helpers.py
    └── validaciones.py
```

## Crear un ejecutable Windows

Realiza el empaquetado desde Windows, con la versión de Python que se usará
para ejecutar la aplicación. Instala las dependencias y PyInstaller:

```bat
py -m pip install -r requirements.txt
py -m pip install pyinstaller
```

Desde la carpeta del proyecto, crea un ejecutable de un solo archivo:

```bat
py -m PyInstaller --noconfirm --clean --onefile --windowed --name TallerApp --add-data "schema.sql;." --collect-all reportlab main.py
```

El ejecutable queda en `dist\TallerApp.exe`.

### Datos y copias de seguridad

- Al ejecutarse como `.exe`, la aplicación mantiene `taller.db` junto al
  ejecutable y crea ese archivo en el primer inicio si aún no existe.
- El esquema `schema.sql` se empaqueta con el ejecutable y solo se usa para
  inicializar una base de datos que todavía no existe.
- Los PDFs se escriben en `pdfs\`, también junto al ejecutable.
- Coloca el ejecutable en una carpeta con permisos de lectura y escritura.
  Evita rutas protegidas como `C:\Program Files`.
- Para respaldar el sistema, cierra la aplicación y copia `taller.db` y la
  carpeta `pdfs\` a otra ubicación. No reemplaces la base de datos de trabajo
  al actualizar el ejecutable.

## Consideraciones

- La app funciona localmente y no requiere internet ni servidor.
- El sistema no calcula IVA ni maneja abonos parciales.
- ReportLab debe estar instalado para generar PDFs.
- En esta etapa no se ha automatizado un instalador de Windows ni un mecanismo
  de actualización de la base de datos existente.
